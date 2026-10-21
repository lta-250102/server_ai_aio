package services

import (
	"context"
	"fmt"
	"image"
	"image/color"
	"log"
	"os"
	"sync"
	"time"

	"github.com/Trendyol/go-triton-client/base"
	gclient "github.com/Trendyol/go-triton-client/client/grpc"
	"gocv.io/x/gocv"
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
	{R: 255, G: 0, B: 0, A: 255}, {R: 0, G: 255, B: 0, A: 255}, {R: 0, G: 0, B: 255, A: 255}, {R: 255, G: 255, B: 0, A: 255},
	{R: 255, G: 0, B: 255, A: 255}, {R: 0, G: 255, B: 255, A: 255}, {R: 128, G: 0, B: 128, A: 255}, {R: 0, G: 128, B: 128, A: 255},
	{R: 128, G: 128, B: 0, A: 255}, {R: 128, G: 0, B: 0, A: 255},
}

// tritonClient là singleton gRPC client (raw base.Client).
var (
	tritonClient base.Client
	clientOnce   sync.Once
)

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
func Detect(ctx context.Context, img gocv.Mat) ([]byte, error) {
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
	outputImg := drawBoxes(img, detections, ratio, padding)
	defer outputImg.Close()

	// 4. Encode JPEG
	return encodeJPEG(outputImg)
}

// --- Internal helpers ---

func letterbox(img gocv.Mat) ([]float32, float64, image.Point, error) {
	const IMG_SIZE = 640
	origW := img.Cols()
	origH := img.Rows()
	ratio := float64(IMG_SIZE) / float64(origW)
	if r2 := float64(IMG_SIZE) / float64(origH); r2 < ratio {
		ratio = r2
	}
	newW := int(float64(origW) * ratio)
	newH := int(float64(origH) * ratio)

	// Resize với INTER_AREA (tương đương cv2.INTER_AREA trong Python)
	resized := gocv.NewMat()
	defer resized.Close()
	gocv.Resize(img, &resized, image.Pt(newW, newH), 0, 0, gocv.InterpolationArea)

	// Tạo ảnh trắng padding (128,128,128)
	padded := gocv.NewMatWithSizeFromScalar(gocv.NewScalar(128, 128, 128, 0), IMG_SIZE, IMG_SIZE, gocv.MatTypeCV8UC3)
	defer padded.Close()

	padX := (IMG_SIZE - newW) / 2
	padY := (IMG_SIZE - newH) / 2

	// Cắt vùng padding để paste resized vào
	roi := padded.Region(image.Rect(padX, padY, padX+newW, padY+newH))
	defer roi.Close()
	resized.CopyTo(&roi)

	// Chuyển sang tensor FP32 NCHW
	pixels := IMG_SIZE * IMG_SIZE
	tensor := make([]float32, pixels*3)

	// Split thành 3 channel
	channels := gocv.Split(padded)
	defer channels[0].Close()
	defer channels[1].Close()
	defer channels[2].Close()
	ch0 := channels[0]
	ch1 := channels[1]
	ch2 := channels[2]

	// Đọc từng channel
	data0, _ := ch0.DataPtrUint8()
	data1, _ := ch1.DataPtrUint8()
	data2, _ := ch2.DataPtrUint8()

	for i := 0; i < pixels; i++ {
		tensor[i] = float32(data0[i]) / 255.0
		tensor[pixels+i] = float32(data1[i]) / 255.0
		tensor[pixels*2+i] = float32(data2[i]) / 255.0
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

func drawBoxes(img gocv.Mat, detections []detection, ratio float64, padding image.Point) gocv.Mat {
	// Clone ảnh gốc để vẽ
	outputImg := img.Clone()

	for _, det := range detections {
		c := _COLORS[det.classID%len(_COLORS)]
		x1 := int((det.bbox[0] - float32(padding.X)) / float32(ratio))
		y1 := int((det.bbox[1] - float32(padding.Y)) / float32(ratio))
		x2 := int((det.bbox[2] - float32(padding.X)) / float32(ratio))
		y2 := int((det.bbox[3] - float32(padding.Y)) / float32(ratio))

		// Vẽ rectangle
		gocv.Rectangle(&outputImg, image.Rect(x1, y1, x2, y2), c, 2)

		// Vẽ label background + text
		label := CLASS_NAMES[det.classID] + " " + fmt.Sprintf("%.2f", det.confidence)
		size := gocv.GetTextSize(label, gocv.FontHersheySimplex, 0.6, 1)
		labelRect := image.Rect(x1, y1-size.Y-6, x1+size.X, y1+4)
		pv := gocv.NewPointsVectorFromPoints([][]image.Point{{
			{X: labelRect.Min.X, Y: labelRect.Min.Y},
			{X: labelRect.Max.X, Y: labelRect.Min.Y},
			{X: labelRect.Max.X, Y: labelRect.Max.Y},
			{X: labelRect.Min.X, Y: labelRect.Max.Y},
		}})
		defer pv.Close()
		gocv.FillPoly(&outputImg, pv, c)
		gocv.PutText(&outputImg, label, image.Pt(x1, y1-int(size.Y)-2), gocv.FontHersheySimplex, 0.6, color.RGBA{R: 255, G: 255, B: 255, A: 255}, 1)
	}

	return outputImg
}

func encodeJPEG(img gocv.Mat) ([]byte, error) {
	buf, err := gocv.IMEncode(gocv.JPEGFileExt, img)
	if err != nil {
		return nil, err
	}
	defer buf.Close()
	return buf.GetBytes(), nil
}
