import json
import requests
import base64
from datetime import datetime

MAX_PAGES = 10
MAX_DAYS_OLD = 45
MAX_RENT = 25000
MIN_AREA = 900
RADIUS = 2
INDEPENDANT_TERMS = ["standalone", "independent"]
BLACKLISTED_LOCATIONS = ["bommasandra"]

seen = set()
locations = []

with open("ignore_list.txt") as file:
    ignores = file.readlines()
    for ignore in ignores:
        seen.add(ignore.strip())

with open("locations.txt") as file:
    dummyLocations = file.readlines()
    # if location doesn't start with hash add it to locations
    for location in dummyLocations:
        if not location.startswith("#"):
            locations.append(location)

def getLocationData(location):
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
        print(response.get("place", {}).get("description"))
        locationData = {
            "lat": response.get("place").get("location").get("lat"),
            "lon": response.get("place").get("location").get("lon"),
            "placeId": placeId,
            "placeName": response.get("place").get("name"),
            "showMap": False
        }
    else: 
        locationData = {}
    return locationData

def filterData(data):
    filteredData = []
    for apartment in data:
        if apartment.get("propertyAge", 0) >= 5:
            continue

        # if rent > 22000, remove it
        rent = apartment.get("rent", 0)
        # if formattedMaintenanceAmount not an empty string, remove comma from it, convert it to integer and add it to rent
        if apartment.get("formattedMaintenanceAmount", ""):
            maintenance = int(apartment.get("formattedMaintenanceAmount").replace(",", ""))
            rent += maintenance
            apartment.update({"rent": rent})

        if rent > MAX_RENT:
            continue

        # if any term in INDEPENDANT_TERMS is in propertyTitle, remove it
        if any(term in apartment.get("propertyTitle", "").lower() for term in INDEPENDANT_TERMS):
            continue
        if any(term in apartment.get("propertyTitle", "").lower() for term in BLACKLISTED_LOCATIONS):
            continue

        # if "bathromm" less than 2 remove it
        if apartment.get("bathroom", 0) < 2:
            continue

        # if "deposit" > 2 lakhs, remove it
        if apartment.get("deposit", 0) > 200000:
            continue

        # if "standalone" in society, remove it
        if any(term in apartment.get("society", "").lower() for term in INDEPENDANT_TERMS):
            continue

        # if "propertySize" < 900, remove it
        if apartment.get("propertySize", 0) < MIN_AREA:
            continue

        # if "floor" is the same as "totalFloors", remove it, only if both have values
        if apartment.get("floor", -99) == apartment.get("totalFloor", -98):
            continue

        # if "thumbnailImage" is "https://assets.nobroker.in/static/img/534_notxt.jpg", ignore it
        if apartment.get("thumbnailImage") == "https://assets.nobroker.in/static/img/534_notxt.jpg":
            continue

        # if creationDate epoch timestamp is more than one month old from now, remove its
        if apartment.get("creationDate", 0) < datetime.now().timestamp() - MAX_DAYS_OLD * 24 * 60 * 60:
            continue


        # In amenitiesMap ensure that "SECURITY" is true
        if not apartment.get("amenitiesMap", {}).get("SECURITY", False):
            continue

        # else add it to filteredData
        filteredData.append(apartment)

    return filteredData

def getApartments():
    apartments = {}
    for location in locations:
        location = location.strip()
        searchParams = [getLocationData(location)]
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
            try:
                response = response.json()
            except Exception as e:
                break
            data = response.get("data", [])
            filteredData = filterData(data)

            for apartment in filteredData:
                url = apartment.get("shortUrl")
                if url not in seen:
                    seen.add(url)
                    if not location in apartments:
                        apartments[location] = []
                    apartments[location].append(apartment)
    return apartments

def main():
    apartments = getApartments()
    for location in apartments:
        print(location)
        print("=====")
        for apartment in apartments[location]:
            # print each property name, and its value
            print(apartment.get("propertyTitle"), "-",apartment.get("rent"))
            print(apartment.get("shortUrl"))
            print("---")

    #print(json.dumps(apartments, indent=2))


if __name__ == "__main__":
    main()
