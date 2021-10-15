package structs

import (
	"time"

	"github.com/shopspring/decimal"
)

type CloudWatchEvent struct {
	CoinToPredict string `json:"coinToPredict"`
}

type HistoricCandles struct {
	Date   time.Time       `csv:"date"`
	Open   decimal.Decimal `csv:"open"`
	High   decimal.Decimal `csv:"high"`
	Low    decimal.Decimal `csv:"low"`
	Close  decimal.Decimal `csv:"close"`
	Volume decimal.Decimal `csv:"volume"`
}

type CloudWatchEventDetails struct {
	EventVersion     string    `json:"eventVersion"`
	EventID          string    `json:"eventID"`
	EventTime        time.Time `json:"eventTime"`
	EventType        string    `json:"eventType"`
	ResponseElements struct {
		OwnerID      string `json:"ownerId"`
		InstancesSet struct {
			Items []struct {
				InstanceID string `json:"instanceId"`
			} `json:"items"`
		} `json:"instancesSet"`
	} `json:"responseElements"`
	AwsRegion    string `json:"awsRegion"`
	EventName    string `json:"eventName"`
	UserIdentity struct {
		UserName    string `json:"userName"`
		PrincipalID string `json:"principalId"`
		AccessKeyID string `json:"accessKeyId"`
		InvokedBy   string `json:"invokedBy"`
		Type        string `json:"type"`
		Arn         string `json:"arn"`
		AccountID   string `json:"accountId"`
	} `json:"userIdentity"`
	EventSource string `json:"eventSource"`
}
