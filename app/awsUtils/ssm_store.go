package awsUtils

import (
	"fmt"
	"log"
	"os"

	awsssm "github.com/PaddleHQ/go-aws-ssm"
	"github.com/spf13/viper"
)

func SetSsmToEnvVars() {

	//Assuming you have the parameters in the following format:
	//my-service/dev/param-1  -> with value `a`
	//my-service/dev/param-2  -> with value `b`
	pmstore, err := awsssm.NewParameterStore()
	if err != nil {
		panic(err)
	}
	//Requesting the base path
	log.Println("Grabbing SSM params for /go-trader/")
	params, err := pmstore.GetAllParametersByPath("/go-trader/", true)
	if err != nil {
		panic(err)
	}

	//Configure viper to handle it as json document, nothing special here!
	v := viper.New()
	v.SetConfigType(`json`)
	//params object implements the io.Reader interface that is required
	log.Printf("Found the folling params %v", params)
	err = v.ReadConfig(params)
	if err != nil {
		panic(err)
	}
	ftxKey := v.Get(`FTX_KEY`)
	ftxSecret := v.Get(`FTX_SECRET`)
	btcSubaccountName := v.Get(`BTC_SUBACCOUNT_NAME`)
	btcFtxKey := v.Get(`BTC_FTX_KEY`)
	btcFtxSecret := v.Get(`BTC_FTX_SECRET`)
	// eth
	ethSubaccountName := v.Get(`ETH_SUBACCOUNT_NAME`)
	ethFtxKey := v.Get(`ETH_FTX_KEY`)
	ethFtxSecret := v.Get(`ETH_FTX_SECRET`)
	// sol
	solSubaccountName := v.Get(`SOL_SUBACCOUNT_NAME`)
	solFtxKey := v.Get(`SOL_FTX_KEY`)
	solFtxSecret := v.Get(`SOL_FTX_SECRET`)
	// matic
	maticSubaccountName := v.Get(`MATIC_SUBACCOUNT_NAME`)
	maticFtxKey := v.Get(`MATIC_FTX_KEY`)
	maticFtxSecret := v.Get(`MATIC_FTX_SECRET`)
	// link
	linkSubaccountName := v.Get(`LINK_SUBACCOUNT_NAME`)
	linkFtxKey := v.Get(`LINK_FTX_KEY`)
	linkFtxSecret := v.Get(`LINK_FTX_SECRET`)
	// polygon API
	alphaVantageKey := v.Get(`ALPHA_VANTAGE_KEY`)

	//value should be `a`
	os.Setenv("FTX_KEY", fmt.Sprintf("%v", ftxKey))
	os.Setenv("FTX_SECRET", fmt.Sprintf("%v", ftxSecret))
	os.Setenv("BTC_SUBACCOUNT_NAME", fmt.Sprintf("%v", btcSubaccountName))
	os.Setenv("BTC_FTX_KEY", fmt.Sprintf("%v", btcFtxKey))
	os.Setenv("BTC_FTX_SECRET", fmt.Sprintf("%v", btcFtxSecret))
	// # ETH
	os.Setenv("ETH_SUBACCOUNT_NAME", fmt.Sprintf("%v", ethSubaccountName))
	os.Setenv("ETH_FTX_KEY", fmt.Sprintf("%v", ethFtxKey))
	os.Setenv("ETH_FTX_SECRET", fmt.Sprintf("%v", ethFtxSecret))
	// SOL
	os.Setenv("SOL_SUBACCOUNT_NAME", fmt.Sprintf("%v", solSubaccountName))
	os.Setenv("SOL_FTX_KEY", fmt.Sprintf("%v", solFtxKey))
	os.Setenv("SOL_FTX_SECRET", fmt.Sprintf("%v", solFtxSecret))
	// MATIC
	os.Setenv("MATIC_SUBACCOUNT_NAME", fmt.Sprintf("%v", maticSubaccountName))
	os.Setenv("MATIC_FTX_KEY", fmt.Sprintf("%v", maticFtxKey))
	os.Setenv("MATIC_FTX_SECRET", fmt.Sprintf("%v", maticFtxSecret))
	// LINK
	os.Setenv("LINK_SUBACCOUNT_NAME", fmt.Sprintf("%v", linkSubaccountName))
	os.Setenv("LINK_FTX_KEY", fmt.Sprintf("%v", linkFtxKey))
	os.Setenv("LINK_FTX_SECRET", fmt.Sprintf("%v", linkFtxSecret))
	// POLYGON
	os.Setenv("ALPHA_VANTAGE_KEY", fmt.Sprintf("%v", alphaVantageKey))
}
