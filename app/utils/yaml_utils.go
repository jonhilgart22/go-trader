package utils

import (
    "bufio"
    "fmt"
    "io"
    "io/ioutil"
    "log"

    "gopkg.in/yaml.v2"
)

func ReadNestedYamlFile(fileLocation string) map[string]map[string]string {
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

func ReadYamlFile(fileLocation string) map[string]string {
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
