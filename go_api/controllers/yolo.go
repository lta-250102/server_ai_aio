package controllers

import (
	"bytes"

	"go_api/services"

	"github.com/gin-gonic/gin"
	"gocv.io/x/gocv"
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

	buf := new(bytes.Buffer)
	buf.ReadFrom(f)

	// Decode từ bytes sang gocv.Mat
	img, err := gocv.IMDecode(buf.Bytes(), gocv.IMReadColor)
	if err != nil || img.Empty() {
		c.JSON(400, gin.H{"error": "invalid image"})
		return
	}
	defer img.Close()

	jpegBytes, err := services.Detect(c.Request.Context(), img)
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
