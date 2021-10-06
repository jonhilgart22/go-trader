package ftx

import (
	"log"
	"time"

	"github.com/grishinsana/goftx"
	"github.com/grishinsana/goftx/models"
	"github.com/shopspring/decimal"
)

func ptrInt(i int) *int {
	return &i
}

func SellOrder(ftxClient *goftx.Client, marketToOrder string) {
	accountBalance, err := ftxClient.Wallet.GetBalances()

	if err != nil {
		panic(err)
	}
	var btcCoinFree decimal.Decimal
	// figure out how much BTC we have
	for _, balance := range accountBalance {
		if balance.Coin == "BTC" {
			btcCoinFree = balance.Free
		}
	}
	log.Printf("Free BTC coin %v", btcCoinFree)
	sellOrder, err := ftxClient.PlaceOrder(&models.PlaceOrderPayload{
		Market: marketToOrder,
		Side:   "sell",
		Size:   btcCoinFree,
		Type:   "market"})
	if err != nil {
		panic(err)
	}
	log.Printf("Sell order = %v", sellOrder)
}

func PurchaseOrder(client *goftx.Client, size decimal.Decimal, marketName string) {

	order, err := client.PlaceOrder(&models.PlaceOrderPayload{
		Market: marketName,
		Side:   "buy",
		Size:   size,
		Type:   "market",
	})
	if err != nil {
		panic(err)
	}
	log.Println(order, "Order")

	// STOP LOSS ORDER

	// trailValue := newestClosePrice.Mul(stopLossPct).Mul(decimal.NewFromFloat32(-1.0))
	// log.Println(trailValue, "Trail Value")

	// stop loss should be handled by Python
	// triggerOrder, err := client.PlaceTriggerOrder(&models.PlaceTriggerOrderPayload{
	// 	Market:     marketName,
	// 	Side:       "sell",
	// 	Size:       size,
	// 	Type:       "trailingStop",
	// 	TrailValue: &trailValue,
	// })
	// if err != nil {
	// 	panic(err)
	// }
	// log.Println("Trigger Order", triggerOrder)
}

func NewClient(key string, secret string, subaccountName string) *goftx.Client {
	client := goftx.New(goftx.WithAuth(
		key,
		secret,
		subaccountName),
		goftx.WithFTXUS())
	return client
}

func PullDataFromFtx(client *goftx.Client, productCode string, resolution int) []*models.HistoricalPrice {

	records, err := client.Markets.GetHistoricalPrices(productCode,
		&models.GetHistoricalPricesParams{
			Resolution: models.Day,
			StartTime:  ptrInt(int(time.Now().Add(-7 * 86400 * time.Second).Unix())), // last 7 days
			EndTime:    ptrInt(int(time.Now().Unix())),
		})

	if err != nil {
		log.Fatal(err)
	}
	log.Println("Pulled records for", productCode)
	log.Println("Records =", records)
	return records
}
