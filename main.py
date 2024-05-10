import json
import requests
import base64

MAX_PAGES = 1
RADIUS = 2

with open("data.json") as file:
    savedData = json.load(file)

def updateSaveData():
    with open("data.json", "w") as file:
        json.dump(savedData, file, indent=2)

with open("locations.txt") as file:
    locations = file.readlines()

def saveLocationData(location):
    response = requests.get(f"https://www.nobroker.in/places/api/v1/autocomplete", params={
        "hint": location, 
        "city": "bangalore",
        "params": "location"
    }, headers={
        "x-tenant-id": "NOBROKER"
    })
    response = response.json()
    if response.get("predictions", []):
        placeId = response["predictions"][0]["placeId"]
        response = requests.get(f"https://www.nobroker.in/places/api/v1/detail/{placeId}", headers={
            "x-tenant-id": "NOBROKER"
        })
        response = response.json()
        locationData = {
            "lat": response.get("place").get("location").get("lat"),
            "lon": response.get("place").get("location").get("lon"),
            "placeId": placeId,
            "placeName": response.get("place").get("name"),
            "showMap": False
        }
    else: 
        locationData = {}
    if not "locations" in savedData:
        savedData["locations"] = {}
    savedData["locations"][location] = locationData
    updateSaveData()

def prepareLocations():
    for location in locations:
        location = location.strip()
        if location not in savedData.get("locations", {}):
            saveLocationData(location)

def filterData(data):
    filteredData = []
    for apartment in data:
        # if property age > 6, remove it
        if apartment.get("propertyAge", 0) > 6:
            continue

        # if rent > 22000, remove it
        if apartment.get("rent", 0) > 22000:
            continue

        # if "standalone" in propertyTitle, ignoring case remove it
        if "standalone" in apartment.get("propertyTitle", "").lower():
            continue

        # if "bathromm" less than 2 remove it
        if apartment.get("bathroom", 0) < 2:
            continue

        # if "deposit" > 2 lakhs, remove it
        if apartment.get("deposit", 0) > 200000:
            continue

        # if "standalone" in society, remove it
        if "standalone" in apartment.get("society", "").lower():
            continue

        # if "propertySize" < 900, remove it
        if apartment.get("propertySize", 0) < 900:
            continue

        # if "floor" is the same as "totalFloors", remove it, only if both have values
        if apartment.get("floor", -99) == apartment.get("totalFloor", -98):
            continue

        # else add it to filteredData
        filteredData.append(apartment)

    return filteredData

def getApartments():
    for location in locations:
        location = location.strip()
        searchParams = [savedData["locations"][location]]
        # convert searchparms to base64 string
        searchParams = json.dumps(searchParams)
        searchParams = searchParams.encode("utf-8")
        searchParams = base64.b64encode(searchParams).decode("utf-8")

        for page in range(1, MAX_PAGES + 1):
            response = requests.get("https://www.nobroker.in/api/v3/multi/property/RENT/filter/nearby", params={
                "pageNo": page,
                "searchParam": searchParams,
                "radius": RADIUS,
                "sharedAccomodation": 0,
                "type": "BHK2",
                "city": "bangalore",
            })
            response = response.json()
            data = response.get("data", [])
            filteredData = filterData(data)

            for apartment in filteredData:
                print(apartment.get("shortUrl"))

            # print(json.dumps(filteredData, indent=2))

def main():
    prepareLocations()
    getApartments()

if __name__ == "__main__":
    main()
