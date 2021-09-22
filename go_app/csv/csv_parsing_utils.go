package csvparsing

import (
	"strconv"
	"time"
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

func ConvertStringToFloat(inputFloat string) float64 {
	const bitSize = 64 // Don't think about it to much. It's just 64 bits.

	float_, err := strconv.ParseFloat(inputFloat, bitSize)
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
