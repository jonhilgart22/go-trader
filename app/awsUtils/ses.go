// taken from https://stackoverflow.com/questions/41176256/how-to-integrate-aws-sdk-ses-in-golang/41181934
package awsUtils

import (
	"log"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ses"
)

func SendEmail(inputMessage string) {

	// toEmail = "jonathan.hilgart@gmail.com" //os.Getenv("TO_EMAIL")
	// subject = "testing"                    //os.Getenv("SUBJECT")

	awsSession, err := session.NewSession(&aws.Config{
		Region: aws.String("us-east-1")},
	)
	if err != nil {
		panic(err)
	}

	sesSession := ses.New(awsSession)

	sesEmailInput := &ses.SendEmailInput{
		Destination: &ses.Destination{
			ToAddresses: []*string{aws.String("jonathan.hilgart@gmail.com")},
		},
		Message: &ses.Message{
			Body: &ses.Body{
				Html: &ses.Content{
					Data: aws.String(inputMessage)},
			},
			Subject: &ses.Content{
				Data: aws.String("Subject"),
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
