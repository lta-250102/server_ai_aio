FROM ghcr.io/hybridgroup/opencv:4.13.0 AS builder

ENV GOPATH /go
ENV CGO_ENABLED=1

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -ldflags="-w -s" -o /go_api ./

FROM ghcr.io/hybridgroup/opencv:4.13.0
WORKDIR /app
COPY --from=builder /go_api /app/go_api
EXPOSE 8090
CMD ["/app/go_api"]
