package csvUtils

import (
	"encoding/csv"
	"fmt"
	"os"
	"time"

	"github.com/shopspring/decimal"

	"github.com/grishinsana/goftx/models"
	"github.com/jonhilgart22/go-trader/app/structs"
)

func ParseDate(inputDate string) time.Time {

	// Declaring layout constant
	const layout = "2006-01-02"

	// Calling Parse() method with its parameters
	tm, _ := time.Parse(layout, inputDate)

	return tm
}

func RoundTimeToDay(inputTime time.Time) time.Time {
	return time.Date(inputTime.Year(), inputTime.Month(), inputTime.Day(), 0, 0, 0, 0, inputTime.Location())
}

func ConvertStringToFloat(inputFloat string) decimal.Decimal {
	const bitSize = 64 // Don't think about it to much. It's just 64 bits.

	float_, err := decimal.NewFromString(inputFloat)
	if err != nil {
		panic(err)
	}

	return float_
}

// contains checks if a string is present in a slice
func Contains(s []string, str string) bool {
	for _, v := range s {
		if v == str {
			return true
		}
	}

	return false
}

func WriteNewCsvData(currentRecords []*models.HistoricalPrice, newestDate time.Time, csvFileName string) int {
	loc, _ := time.LoadLocation("UTC")
	today := time.Now().In(loc)
	roundedToday := RoundTimeToDay(today)

	numRecordsWritten := 0
	for _, currentVal := range currentRecords {
		fmt.Println("currentVal", currentVal)

		if currentVal.StartTime.After(newestDate) && !currentVal.StartTime.Equal(roundedToday) { // add this data, but not today's data
			fmt.Println("Adding data from this date =", currentVal.StartTime)

			f, err := os.OpenFile(csvFileName, os.O_WRONLY|os.O_CREATE|os.O_APPEND, 0644)
			if err != nil {
				fmt.Println(err)
				return 0
			}
			w := csv.NewWriter(f)
			// csv format is date,open,high,low,close,volume
			// need to convert all to strings
			w.Write([]string{
				fmt.Sprintf("%d-%02d-%02d",
					currentVal.StartTime.Year(),
					currentVal.StartTime.Month(),
					currentVal.StartTime.Day()),
				fmt.Sprintf("%v", currentVal.Open),
				fmt.Sprintf("%v", currentVal.High),
				fmt.Sprintf("%v", currentVal.Low),
				fmt.Sprintf("%v", currentVal.Close),
				fmt.Sprintf("%v", currentVal.Volume)})
			w.Flush()
			numRecordsWritten += 1
		}
	}
	return numRecordsWritten
}

func FindNewestData(inputRecords []structs.HistoricCandles) (time.Time, decimal.Decimal) {
	var newestDate time.Time
	var newestClosePrice decimal.Decimal
	for _, historicVal := range inputRecords {
		if historicVal.Date.After(newestDate) {
			newestDate = historicVal.Date
			newestClosePrice = historicVal.Close
		}
	}

	return newestDate, newestClosePrice
}
