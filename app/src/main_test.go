package main

import (
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/grishinsana/goftx/models"
	"github.com/johannesboyne/gofakes3"
	"github.com/johannesboyne/gofakes3/backend/s3mem"
	"github.com/shopspring/decimal"
	"github.com/spf13/afero"
)

func setupHIstoricalPrice() []*models.HistoricalPrice {
	historicalData := []*models.HistoricalPrice{}

	dayOneOpen, err := decimal.NewFromString("900.0")
	if err != nil {
		panic(err)
	}
	dayOneHigh, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayOneClose, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayOneVolume, err := decimal.NewFromString("3000.0")
	if err != nil {
		panic(err)
	}
	dayTwoOpen, err := decimal.NewFromString("900.0")
	if err != nil {
		panic(err)
	}
	dayTwoHigh, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayTwoClose, err := decimal.NewFromString("300.0")
	if err != nil {
		panic(err)
	}
	dayTwoVolume, err := decimal.NewFromString("3000.0")
	if err != nil {
		panic(err)
	}
	dayThreeOpen, err := decimal.NewFromString("9300.0")
	if err != nil {
		panic(err)
	}
	dayThreeHigh, err := decimal.NewFromString("6300.0")
	if err != nil {
		panic(err)
	}
	dayThreeClose, err := decimal.NewFromString("30340.0")
	if err != nil {
		panic(err)
	}
	dayThreeVolume, err := decimal.NewFromString("304500.0")
	if err != nil {
		panic(err)
	}

	dayOne := models.HistoricalPrice{StartTime: time.Date(2017, time.Month(1), 6, 0, 0, 0, 0, time.UTC),
		Open:   dayOneOpen,
		High:   dayOneHigh,
		Close:  dayOneClose,
		Volume: dayOneVolume}
	historicalData = append(historicalData, &dayOne)

	dayTwo := models.HistoricalPrice{StartTime: time.Date(2017, time.Month(1), 7, 0, 0, 0, 0, time.UTC),
		Open:   dayTwoOpen,
		High:   dayTwoHigh,
		Close:  dayTwoClose,
		Volume: dayTwoVolume}
	historicalData = append(historicalData, &dayTwo)

	// we shouldn't include today's data
	dayThree := models.HistoricalPrice{StartTime: time.Date(2017, time.Month(1), 8, 0, 0, 0, 0, time.UTC),
		Open:   dayThreeOpen,
		High:   dayThreeHigh,
		Close:  dayThreeClose,
		Volume: dayThreeVolume}
	historicalData = append(historicalData, &dayThree)

	return historicalData
}

func TestDownloadUpdateReuploadData(t *testing.T) {
	// mock the ftx client with fake data, and the fake data is the same as the real data, call the endpoint, get the fake data, update it with the newest date, and reupload it
	const bucketName = "go-trader"
	const fileName = "test_csv_data.csv"
	constantsMap := map[string]string{"s3_bucket": bucketName, "s3_file_name": fileName}

	historicalPrices := setupHIstoricalPrice()

	// fake s3
	backend := s3mem.New()
	faker := gofakes3.New(backend)
	ts := httptest.NewServer(faker.Server())
	defer ts.Close()

	// configure S3 client
	s3Config := &aws.Config{
		Credentials:      credentials.NewStaticCredentials("YOUR-ACCESSKEYID", "YOUR-SECRETACCESSKEY", ""),
		Endpoint:         aws.String(ts.URL),
		Region:           aws.String("us-east-1"),
		DisableSSL:       aws.Bool(true),
		S3ForcePathStyle: aws.Bool(true),
	}
	newSession := session.New(s3Config)

	s3Client := s3.New(newSession)
	cparams := &s3.CreateBucketInput{
		Bucket: aws.String(bucketName),
	}

	// Create a new bucket using the CreateBucket call.
	_, err := s3Client.CreateBucket(cparams)
	if err != nil {
		// Message from an error.
		t.Log(err.Error())
		return
	}

	// Upload a fake csv file to the bucket
	// 			date,open,high,low,close,volume

	_, err = s3Client.PutObject(&s3.PutObjectInput{
		Body:   strings.NewReader(`2017-01-03,225.04,225.83,223.8837,225.24,91087570` + "\n" + `2017-01-04,225.62,226.75,225.61,226.58,78458530` + "\n" + `2017-01-05,226.27,226.58,225.48,226.4,78291080`),
		Bucket: aws.String(bucketName),
		Key:    aws.String(fileName),
	})

	params := &s3.ListObjectsInput{
		Bucket: aws.String(bucketName),
	}

	resp, _ := s3Client.ListObjects(params)
	for _, key := range resp.Contents {
		t.Log(*key.Key)
	}

	newestClosePrice, numRecordsWritten := DownloadUpdateReuploadData(fileName, historicalPrices, constantsMap, false, newSession)

	respNew, _ := s3Client.ListObjects(params)
	for _, key := range respNew.Contents {
		t.Log(*key.Key, "new key")
		if *key.Key != fileName {
			t.Fail()
		}
	}

	t.Log("newestClosePrice: ", newestClosePrice)
	t.Log("numRecordsWritten", numRecordsWritten)

	tolerance := decimal.NewFromFloat(.00001)
	if newestClosePrice.Sub(decimal.NewFromFloat(226.4)).GreaterThan(tolerance) {
		t.Fail()
	}

	if numRecordsWritten != 3 {
		t.Fail()
	}
}

func TestIterateAndUploadTmpFiles(t *testing.T) {
	// create a fake directory with two .yml files in it
	var AppFs = afero.NewOsFs()
	var bucketName = "test-bucket"
	constantsMap := map[string]string{"s3_bucket": bucketName}

	AppFs.MkdirAll("/tmp/", os.ModePerm)

	//create file inside tmp directory
	AppFs.Create("/tmp/test_file_1.yml")
	AppFs.Create("/tmp/test_file_1.csv")
	AppFs.Create("/tmp/test_file_1.png")

	// create fake s3
	// fake s3
	backend := s3mem.New()
	faker := gofakes3.New(backend)
	ts := httptest.NewServer(faker.Server())
	defer ts.Close()

	// configure S3 client
	s3Config := &aws.Config{
		Credentials:      credentials.NewStaticCredentials("YOUR-ACCESSKEYID", "YOUR-SECRETACCESSKEY", ""),
		Endpoint:         aws.String(ts.URL),
		Region:           aws.String("us-east-1"),
		DisableSSL:       aws.Bool(true),
		S3ForcePathStyle: aws.Bool(true),
	}
	newSession := session.New(s3Config)

	s3Client := s3.New(newSession)
	s3Params := &s3.CreateBucketInput{
		Bucket: aws.String(bucketName),
	}
	s3ListBucket := &s3.ListObjectsInput{
		Bucket: aws.String(bucketName),
	}

	// Create a new bucket using the CreateBucket call.
	_, err := s3Client.CreateBucket(s3Params)
	if err != nil {
		// Message from an error.
		t.Log(err.Error())
		return
	}

	IterateAndUploadTmpFiles("/tmp/", constantsMap, true, newSession)

	// list the files that were uploaded
	respNew, _ := s3Client.ListObjects(s3ListBucket)
	for _, key := range respNew.Contents {
		t.Log(*key.Key, "new key")
		// make sure the tmp/ is added back and that we only upload the yml
		if *key.Key != "tmp/test_file_1.yml" {
			t.Fail()
		}
	}
}
