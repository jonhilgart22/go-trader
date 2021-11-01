// taken from https://stackoverflow.com/questions/41176256/how-to-integrate-aws-sdk-ses-in-golang/41181934
package awsUtils

import (
	"io/ioutil"
	"log"
	"os"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ses"
)

func readTextFile(fileName string) string {
	// for testing locally, need to run the python code to create the logs.txt file.
	log.Printf("Attempting to open %s", fileName)
	file, err := os.Open(fileName)
	if err != nil {
		log.Fatal(err)
	}
	defer func() {
		if err = file.Close(); err != nil {
			log.Fatal(err)
		}
	}()

	b, err := ioutil.ReadAll(file)
	if err != nil {
		panic(err)
	}
	return string(b)

}
func SendEmail(inputSubject string, logsFilename string, onAws bool) {
	var body string
	if onAws {
		body = readTextFile("/tmp/" + logsFilename)
	} else {
		body = readTextFile(logsFilename)
	}

	awsSession, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1")},
	)
	if err != nil {
		panic(err)
	}

	sesSession := ses.New(awsSession)

	sesEmailInput := &ses.SendEmailInput{
		Destination: &ses.Destination{
			ToAddresses: []*string{aws.String("jonathan.hilgart@gmail.com"), aws.String("justin.hilgart@gmail.com")},
		},
		Message: &ses.Message{
			Body: &ses.Body{
				Html: &ses.Content{
					Data: aws.String(string(body))},
			},
			Subject: &ses.Content{
				Data: aws.String(inputSubject),
			},
		},
		Source: aws.String("jonathan.hilgart@gmail.com"),
		ReplyToAddresses: []*string{
			aws.String("jonathan.hilgart@gmail.com"),
		},
	}

	result, err := sesSession.SendEmail(sesEmailInput)
	if err != nil {
		panic(err)
	} else {
		log.Printf("Email sent with result %v", result)
	}
}
