package awsUtils

import (
	"bytes"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/s3/s3manager"
)

func RunningOnAws() bool {
	val, present := os.LookupEnv("AWS_EXECUTION_ENV")
	log.Println("Looking up env var ", val)
	return present
}

func DownloadFromS3(bucket string, item string, onAws bool) {

	// 2) Create an AWS session
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1")},
	)
	if err != nil {
		panic(err)
	}

	// 3) Create a new AWS S3 downloader
	downloader := s3manager.NewDownloader(sess)

	// 4) Download the item from the bucket. If an error occurs, log it and exit. Otherwise, notify the user that the download succeeded.
	s3Item := item
	if onAws {
		// download with tmp/, keep the same path in S3.
		s := strings.Split(item, "/")
		item = "/tmp/" + s[len(s)-1]
	}
	// NOTE: you need to store your AWS credentials in ~/.aws/credentials or in env vars
	log.Printf("Attempting to download file %v from bucket %v", item, bucket)

	file, err := os.Create(item)
	if err != nil {
		log.Fatalf("Unable to create item %q, %v", item, err)
	}
	defer file.Close()

	numBytes, err := downloader.Download(file,
		&s3.GetObjectInput{
			Bucket: aws.String(bucket),
			Key:    aws.String(s3Item),
		})
	if err != nil {
		log.Fatalf("Unable to download item %q, %v", item, err)
	}

	log.Println("Downloaded", file.Name(), numBytes, "bytes")

}

func UploadToS3(bucket string, item string, runningOnAws bool) {
	var s3Item string
	if runningOnAws {
		s3Item = item
		s := strings.Split(item, "/")
		item = "/tmp/" + s[len(s)-1]
	} else {
		s3Item = item
	}
	//  Create an AWS session
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1")},
	)
	if err != nil {
		log.Fatal(err)
	}

	// open the file for use
	file, err := os.Open(item)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	// get the file size and read
	// the file content into a buffer
	fileInfo, _ := file.Stat()
	var size = fileInfo.Size()
	buffer := make([]byte, size)
	file.Read(buffer)

	// config settings: this is where you choose the bucket,
	// filename, content-type and storage class of the file
	// you're uploading
	_, s3err := s3.New(sess).PutObject(&s3.PutObjectInput{
		Bucket:               aws.String(bucket),
		Key:                  aws.String(s3Item),
		ACL:                  aws.String("private"),
		Body:                 bytes.NewReader(buffer),
		ContentLength:        aws.Int64(size),
		ContentType:          aws.String(http.DetectContentType(buffer)),
		ContentDisposition:   aws.String("attachment"),
		ServerSideEncryption: aws.String("AES256"),
		StorageClass:         aws.String("INTELLIGENT_TIERING"),
	})

	if s3err != nil {
		log.Fatal(err)
	}

	log.Println("Upload successful of file ", item)
}
