package yahoo

import (
	"log"
	"time"

	"github.com/grishinsana/goftx/models"
	"github.com/markcheno/go-quote"
	"github.com/shopspring/decimal"
)

func PullDataFromYahoo(productCode string) []*models.HistoricalPrice {

	// pull data from 14 days ago to today
	log.Println("Pulling data from Yahoo")
	tbt, _ := quote.NewQuoteFromYahoo(
		productCode,
		time.Now().Add(-14*172800*time.Second).Format("2006-01-02"),
		time.Now().Format("2006-01-02"),
		quote.Daily, true)
	var records []*models.HistoricalPrice

	for idx := 0; idx < len(tbt.Close); idx++ {
		open := decimal.NewFromFloat(tbt.Open[idx])
		high := decimal.NewFromFloat(tbt.High[idx])
		low := decimal.NewFromFloat(tbt.Low[idx])
		close := decimal.NewFromFloat(tbt.Close[idx])
		volume := decimal.NewFromFloat(tbt.Volume[idx])

		records = append(records, &models.HistoricalPrice{
			StartTime: tbt.Date[idx],
			Open:      open,
			High:      high,
			Low:       low,
			Close:     close,
			Volume:    volume,
		})
		log.Println(records)
	}

	return records

}
