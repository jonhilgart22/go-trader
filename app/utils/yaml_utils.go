package utils

import (
	"bufio"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"strings"

	"gopkg.in/yaml.v2"
)

func ReadNestedYamlFile(fileLocation string, runningOnAws bool, coinToPredict string) map[string]map[string]string {

	// every file have the coin name as the first level
	splitFilename := strings.Split(fileLocation, "/")
	fileLocation = splitFilename[0] + "/" + coinToPredict + "_" + splitFilename[1]
	log.Println("fileLocation = ", fileLocation)

	if runningOnAws {
		// download with tmp/, keep the same path in S3.
		s := strings.Split(fileLocation, "/")
		fileLocation = "/tmp/" + s[len(s)-1]
	}

	log.Println(" ")
	yfile, err := ioutil.ReadFile(fileLocation)

	if err != nil {
		panic(err)
	}
	doubleLevelData := make(map[string]map[string]string)
	errDouble := yaml.Unmarshal(yfile, &doubleLevelData)
	if errDouble != nil {
		panic(errDouble)
	} else {
		for k, v := range doubleLevelData {

			fmt.Printf("%s -> %s\n", k, v)

		}
		log.Println("Finished reading in yaml constants")
		log.Println(" ")
	}
	return doubleLevelData
}

func ReadYamlFile(fileLocation string, runningOnAws bool, coinToPredict string) map[string]string {
	if len(coinToPredict) == 3 {
		// every file have the coin name as the first level
		splitFilename := strings.Split(fileLocation, "/")
		fileLocation = splitFilename[0] + "/" + coinToPredict + "_" + splitFilename[1]
		log.Println("fileLocation = ", fileLocation)
	}

	if runningOnAws {
		// download with tmp/, keep the same path in S3.
		s := strings.Split(fileLocation, "/")
		fileLocation = "/tmp/" + s[len(s)-1]
	}
	log.Println(" ")
	yfile, err := ioutil.ReadFile(fileLocation)

	if err != nil {
		panic(err)
	}
	singleLevelData := make(map[string]string)

	errSingle := yaml.Unmarshal(yfile, &singleLevelData)
	if errSingle != nil {
		log.Println("Signle level didn't work, test two levels")
	} else {
		for k, v := range singleLevelData {

			fmt.Printf("%s -> %s\n", k, v)

		}
		log.Println("Finished reading in yaml constants")
		log.Println(" ")
	}
	return singleLevelData

}

func CopyOutput(r io.Reader) {
	scanner := bufio.NewScanner(r)
	for scanner.Scan() {
		log.Println(scanner.Text())
	}
}
