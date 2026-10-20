package controllers

import (
	"image"
	"image/draw"

	"go_api/services"

	"github.com/gin-gonic/gin"
)

// Detect godoc: POST /yolo/detect with multipart form field "image".
// Returns JPEG image with bounding boxes drawn.
func Detect(c *gin.Context) {
	f, _, err := c.Request.FormFile("image")
	if err != nil {
		c.JSON(400, gin.H{"error": "missing image field: " + err.Error()})
		return
	}
	defer f.Close()

	img, _, err := image.Decode(f)
	if err != nil {
		c.JSON(400, gin.H{"error": "invalid image: " + err.Error()})
		return
	}

	bounds := img.Bounds()
	nrgbaImg := image.NewNRGBA(bounds)
	draw.Draw(nrgbaImg, bounds, img, bounds.Min, draw.Src)

	jpegBytes, err := services.Detect(c.Request.Context(), nrgbaImg)
	if err != nil {
		c.JSON(500, gin.H{"error": "detection failed: " + err.Error()})
		return
	}

	c.Data(200, "image/jpeg", jpegBytes)
}

// Health godoc: GET /yolo/health.
func Health(c *gin.Context) {
	c.JSON(200, gin.H{"status": "ok"})
}
