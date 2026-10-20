FROM golang:1.26-alpine AS builder
RUN apk --no-cache add git
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /go_api ./
FROM alpine:3.20
RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY --from=builder /go_api /app/go_api
EXPOSE 8080
CMD ["/app/go_api"]
