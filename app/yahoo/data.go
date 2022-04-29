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
	log.Println("Pulling data from Yahoo complete")
	log.Println("TBT data = ", tbt.CSV())
	var records []*models.HistoricalPrice

	newestDate := time.Date(2017, time.Month(1), 7, 0, 0, 0, 0, time.UTC)
	// check if the newest date we have is not today's date (UTC). If so, we're on a weekend or holiday when markets are closed
	// need to take the last row and propagae it forward to today

	for idx := 0; idx < len(tbt.Close); idx++ {
		open := decimal.NewFromFloat(tbt.Open[idx])
		high := decimal.NewFromFloat(tbt.High[idx])
		low := decimal.NewFromFloat(tbt.Low[idx])
		close := decimal.NewFromFloat(tbt.Close[idx])
		volume := decimal.NewFromFloat(tbt.Volume[idx])

		date := tbt.Date[idx]

		if date.After(newestDate) {
			log.Println("Updating the newest date to be ", date)
			newestDate = date
		}

		records = append(records, &models.HistoricalPrice{
			StartTime: date,
			Open:      open,
			High:      high,
			Low:       low,
			Close:     close,
			Volume:    volume,
		})
	}
	log.Println(newestDate, "newestDate")

	// Defining duration
	d := (24 * time.Hour)
	loc, _ := time.LoadLocation("UTC")
	missingDaysDelta := time.Now().In(loc).Truncate(d).Sub(newestDate).Hours() / 24
	missingDaysDelta -= 1
	log.Println(missingDaysDelta, "missingDaysDelta")
	// subtract one to exclude the current date

	// for each day that we are missing , except for today, duplicate the last row via calls to the Yahoo API
	lastRecord := records[len(records)-1]
	log.Println("original last record", lastRecord)

	for i := 0; i < int(missingDaysDelta); i++ {
		dateAdd := i + 1

		// create a copy of the last record
		newLastRecord := &models.HistoricalPrice{
			StartTime: lastRecord.StartTime,
			Open:      lastRecord.Open,
			High:      lastRecord.High,
			Low:       lastRecord.Low,
			Close:     lastRecord.Close,
			Volume:    lastRecord.Volume,
		}
		newLastRecord.StartTime = newestDate.Truncate(d).AddDate(0, 0, dateAdd)
		log.Println(newLastRecord, "newLastRecord")

		records = append(records, newLastRecord)
	}

	return records

}
