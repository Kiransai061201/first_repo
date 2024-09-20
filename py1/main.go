package main

import (
	"fmt"
	"io"
	"net/http"
)

func main() {

	url := "https://moviesdatabase.p.rapidapi.com/titles"

	req, _ := http.NewRequest("GET", url, nil)

	req.Header.Add("x-rapidapi-key", "51156b7684mshc07d1beddf99fdbp1cbc1bjsncf984ec67efc")
	req.Header.Add("x-rapidapi-host", "moviesdatabase.p.rapidapi.com")

	res, _ := http.DefaultClient.Do(req)

	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)

	fmt.Println(res)
	fmt.Println(string(body))

}
