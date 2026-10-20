package services

import (
	"bytes"
	"context"
	"fmt"
	"image"
	"image/color"
	"image/draw"
	"image/jpeg"
	"log"
	"os"
	"sync"
	"time"

	"github.com/Trendyol/go-triton-client/base"
	gclient "github.com/Trendyol/go-triton-client/client/grpc"
	"github.com/disintegration/imaging"
	"golang.org/x/image/font"
	"golang.org/x/image/font/basicfont"
	"golang.org/x/image/math/fixed"
	"google.golang.org/grpc/keepalive"
)

// CLASS_NAMES là danh sách 80 classes COCO.
var CLASS_NAMES = []string{
	"person", "bicycle", "car", "motorcycle",
	"airplane", "bus", "train", "truck",
	"boat", "traffic light", "fire hydrant",
	"stop sign", "parking meter", "bench",
	"bird", "cat", "dog", "horse",
	"sheep", "cow", "elephant", "bear",
	"zebra", "giraffe", "backpack", "umbrella",
	"handbag", "tie", "suitcase", "frisbee",
	"skis", "snowboard", "sports ball",
	"kite", "baseball bat", "baseball glove",
	"skateboard", "surfboard", "tennis racket",
	"bottle", "wine glass", "cup", "fork",
	"knife", "spoon", "bowl", "banana",
	"apple", "sandwich", "orange", "broccoli",
	"carrot", "hot dog", "pizza", "donut",
	"cake", "chair", "couch", "potted plant",
	"bed", "dining table", "toilet", "tv",
	"laptop", "mouse", "remote", "keyboard",
	"cell phone", "microwave", "oven", "toaster",
	"sink", "refrigerator", "book", "clock",
	"vase", "scissors", "teddy bear", "hair drier",
	"toothbrush",
}

// _COLORS là màu RGB cho các classes.
var _COLORS = []color.RGBA{
	{255, 0, 0, 255}, {0, 255, 0, 255}, {0, 0, 255, 255}, {255, 255, 0, 255},
	{255, 0, 255, 255}, {0, 255, 255, 255}, {128, 0, 128, 255}, {0, 128, 128, 255},
	{128, 128, 0, 255}, {128, 0, 0, 255},
}

// tritonClient là singleton gRPC client (raw base.Client).
var (
	tritonClient base.Client
	clientOnce   sync.Once
)

// face là font face dùng chung (7x13 pixels, có sẵn trong thư viện).
var face = basicfont.Face7x13

// InitTritonPool khởi tạo singleton pool. Gọi 1 lần khi app start.
func InitTritonPool() error {
	var err error
	clientOnce.Do(func() {
		host := os.Getenv("TRITON_HOST")
		if host == "" {
			host = "localhost"
		}
		endpoint := host + ":8001"
		keepAlive := &keepalive.ClientParameters{
			Time:                10 * time.Second,
			Timeout:             20 * time.Second,
			PermitWithoutStream: true,
		}
		tritonClient, err = gclient.NewClient(endpoint, false, 3, 3, false, true, keepAlive, log.Default())
		if err != nil {
			err = fmt.Errorf("create triton client: %w", err)
		}
	})
	return err
}

// Detect thực hiện inference YOLO và trả về ảnh JPEG với bounding boxes.
func Detect(ctx context.Context, img *image.NRGBA) ([]byte, error) {
	// 1. Letterbox: resize + padding
	tensor, ratio, padding, err := letterbox(img)
	if err != nil {
		return nil, fmt.Errorf("letterbox: %w", err)
	}

	// 2. Infer
	detections, err := infer(ctx, tensor)
	if err != nil {
		return nil, err
	}

	// 3. Vẽ boxes lên ảnh gốc
	rgbaImg := image.NewRGBA(img.Bounds())
	draw.Draw(rgbaImg, img.Bounds(), img, image.Point{}, draw.Src)
	outputImg := drawBoxes(rgbaImg, detections, ratio, padding)

	// 4. Encode JPEG
	return encodeJPEG(outputImg)
}

// --- Internal helpers ---

func letterbox(img *image.NRGBA) ([]float32, float64, image.Point, error) {
	const IMG_SIZE = 640
	bounds := img.Bounds()
	origW := bounds.Dx()
	origH := bounds.Dy()
	ratio := float64(IMG_SIZE) / float64(origW)
	if r2 := float64(IMG_SIZE) / float64(origH); r2 < ratio {
		ratio = r2
	}
	newW := int(float64(origW) * ratio)
	newH := int(float64(origH) * ratio)

	resized := imaging.Resize(img, newW, newH, imaging.Box)

	padX := (IMG_SIZE - newW) / 2
	padY := (IMG_SIZE - newH) / 2
	padded := image.NewNRGBA(image.Rect(0, 0, IMG_SIZE, IMG_SIZE))
	for y := 0; y < IMG_SIZE; y++ {
		for x := 0; x < IMG_SIZE; x++ {
			idx := y*IMG_SIZE*4 + x*4
			padded.Pix[idx] = 128
			padded.Pix[idx+1] = 128
			padded.Pix[idx+2] = 128
			padded.Pix[idx+3] = 255
		}
	}
	for y := 0; y < newH; y++ {
		for x := 0; x < newW; x++ {
			padded.Set(x+padX, y+padY, resized.At(x, y))
		}
	}

	// Chuyển sang tensor FP32 NCHW
	pixels := IMG_SIZE * IMG_SIZE
	tensor := make([]float32, pixels*3)

	for y := 0; y < IMG_SIZE; y++ {
		for x := 0; x < IMG_SIZE; x++ {
			pixIdx := y*IMG_SIZE*4 + x*4
			// NCHW: C * H * W + H * W + W * y + x
			idx := y*IMG_SIZE + x
			tensor[idx] = float32(padded.Pix[pixIdx]) / 255.0
			tensor[pixels+idx] = float32(padded.Pix[pixIdx+1]) / 255.0
			tensor[pixels*2+idx] = float32(padded.Pix[pixIdx+2]) / 255.0
		}
	}

	return tensor, ratio, image.Point{padX, padY}, nil
}

type detection struct {
	classID    int
	confidence float32
	bbox       [4]float32
}

func infer(ctx context.Context, tensor []float32) ([]detection, error) {
	shape := []int64{1, 3, 640, 640}
	input := gclient.NewInferInput("images", "FP32", shape, nil)
	if err := input.SetData(tensor, false); err != nil {
		return nil, fmt.Errorf("set input: %w", err)
	}

	output := []base.InferOutput{gclient.NewInferOutput("output0", map[string]any{"binary_data": true})}

	resp, err := tritonClient.Infer(ctx, "yolo_det", "1", []base.InferInput{input}, output, nil)
	if err != nil {
		return nil, fmt.Errorf("triton infer: %w", err)
	}

	slice, err := resp.AsFloat32Slice("output0")
	if err != nil {
		return nil, fmt.Errorf("parse result: %w", err)
	}

	var results []detection
	for i := 0; i+5 < len(slice); i += 6 {
		conf := slice[i+4]
		if conf < 0.25 {
			continue
		}
		classID := int(slice[i+5])
		if classID >= len(CLASS_NAMES) {
			continue
		}
		results = append(results, detection{
			classID:    classID,
			confidence: conf,
			bbox:       [4]float32{slice[i], slice[i+1], slice[i+2], slice[i+3]},
		})
	}
	return results, nil
}

func drawBoxes(img *image.RGBA, detections []detection, ratio float64, padding image.Point) *image.RGBA {
	output := image.NewRGBA(img.Bounds())
	draw.Draw(output, img.Bounds(), img, image.Point{0, 0}, draw.Src)

	for _, det := range detections {
		c := _COLORS[det.classID%len(_COLORS)]
		x1 := (det.bbox[0] - float32(padding.X)) / float32(ratio)
		y1 := (det.bbox[1] - float32(padding.Y)) / float32(ratio)
		x2 := (det.bbox[2] - float32(padding.X)) / float32(ratio)
		y2 := (det.bbox[3] - float32(padding.Y)) / float32(ratio)

		drawRect(output, image.Point{int(x1), int(y1)}, image.Point{int(x2), int(y2)}, c, 2)

		label := CLASS_NAMES[det.classID] + " " + fmt.Sprintf("%.2f", det.confidence)
		tw := measureTextWidth(label)
		th := face.Metrics().Height.Ceil()
		drawRect(output,
			image.Point{int(x1), int(y1) - th - 6},
			image.Point{int(x1) + tw, int(y1) + 4},
			c, -1)
		putText(output, label, image.Point{int(x1), int(y1) - th - 2}, color.RGBA{255, 255, 255, 255})
	}
	return output
}

func measureTextWidth(text string) int {
	return int(font.MeasureString(face, text).Ceil())
}

func drawRect(img *image.RGBA, pt1, pt2 image.Point, c color.RGBA, thickness int) {
	for x := pt1.X; x <= pt2.X; x++ {
		for y := 0; y < thickness; y++ {
			if py := pt1.Y + y; py >= 0 && py < img.Bounds().Dy() {
				img.Set(x, py, c)
				img.Set(x, pt2.Y+y, c)
			}
		}
	}
	for y := pt1.Y; y <= pt2.Y; y++ {
		for x := 0; x < thickness; x++ {
			if px := pt1.X + x; px >= 0 && px < img.Bounds().Dx() {
				img.Set(px, y, c)
				img.Set(pt2.X+x, y, c)
			}
		}
	}
}

func putText(img *image.RGBA, text string, pt image.Point, c color.RGBA) {
	d := &font.Drawer{
		Dst:  img,
		Src:  image.NewUniform(c),
		Face: face,
		Dot:  fixed.Point26_6{X: fixed.I(pt.X), Y: fixed.I(pt.Y)},
	}
	d.DrawString(text)
}

func encodeJPEG(img image.Image) ([]byte, error) {
	buf := new(bytes.Buffer)
	if err := jpeg.Encode(buf, img, &jpeg.Options{Quality: 90}); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}
