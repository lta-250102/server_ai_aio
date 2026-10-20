package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"go_api/controllers"
	"go_api/services"

	"github.com/gin-gonic/gin"
)

func main() {
	// Khởi tạo singleton Triton client.
	if err := services.InitTritonPool(); err != nil {
		log.Fatalf("failed to init triton client: %v", err)
	}

	engine := gin.Default()
	yolo := engine.Group("/yolo")
	{
		yolo.GET("/health", controllers.Health)
		yolo.POST("/detect", controllers.Detect)
	}

	srv := &http.Server{Addr: ":8090", Handler: engine}

	// Graceful shutdown.
	var once sync.Once
	go func() {
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
		<-quit
		once.Do(func() {
			log.Println("shutting down...")
			ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
			defer cancel()
			srv.Shutdown(ctx)
		})
	}()

	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}
