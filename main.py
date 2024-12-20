import json
import requests
import base64
from datetime import datetime

MAX_PAGES = 10
MAX_DAYS_OLD = 45
MAX_RENT = 50000
MIN_AREA = 900
RADIUS = 2
INDEPENDANT_TERMS = []
# INDEPENDANT_TERMS = ["standalone", "independent"]
BLACKLISTED_LOCATIONS = ["bommasandra"]
CITY = "bangalore"
BHK = 2

seen = set()
locations = []
fullNames = {}

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
        "city": CITY,
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
        fullNames[location] = response.get("place", {}).get("description")
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
        score = 0

        if len(apartment.get("photos", [])) < 4:
            score -= 10

        if apartment.get("propertyAge", 0) >= 10:
            continue

        # younger the building is better the score
        score += 6 - apartment.get("propertyAge", 5)

        # if rent > MAX_RENT, remove it
        rent = apartment.get("rent", 0)
        # if formattedMaintenanceAmount not an empty string, remove comma from it, convert it to integer and add it to rent
        if apartment.get("formattedMaintenanceAmount", ""):
            maintenance = int(apartment.get("formattedMaintenanceAmount").replace(",", ""))
            rent += maintenance
            apartment.update({"rent": rent})
            apartment.update({"maintenance": maintenance})

        if rent > MAX_RENT:
            continue

        # if any term in INDEPENDANT_TERMS is in propertyTitle, remove it
        if apartment.get("buildingType", "").lower() == "ih":
            score -= 3
            continue
        if any(term in apartment.get("propertyTitle", "").lower() for term in INDEPENDANT_TERMS) or any(term in apartment.get("secondaryTitle", "").lower() for term in INDEPENDANT_TERMS):
            score-=3
            continue
        if any(term in apartment.get("propertyTitle", "").lower() for term in BLACKLISTED_LOCATIONS):
            continue

        # if "bathromm" less than 2 remove it
        #if apartment.get("bathroom", 0) < 2:
            #continue

        # if "deposit" > 2 lakhs, remove it
        #if apartment.get("deposit", 0) > 200000:
        #    continue

        # if "standalone" in society, remove it
        if any(term in apartment.get("society", "").lower() for term in INDEPENDANT_TERMS):
            score -= 3
            #continue

        # if "propertySize" < MIN_AREA, remove it
        if apartment.get("propertySize", 0) < MIN_AREA:
            continue

        # if "floor" is the same as "totalFloors", remove it, only if both have values
        if apartment.get("floor", -99) == apartment.get("totalFloor", -98):
            continue

        # if "thumbnailImage" is "https://assets.nobroker.in/static/img/534_notxt.jpg", ignore it
        #if apartment.get("thumbnailImage") == "https://assets.nobroker.in/static/img/534_notxt.jpg":
        #    continue

        # if creationDate epoch timestamp is more than one month old from now, remove its
        if apartment.get("activationDate", 0) < datetime.now().timestamp() - MAX_DAYS_OLD * 24 * 60 * 60:
            continue

        # if parking is NONE, remove it
        if apartment.get("parking", "").lower() == "none":
            score -= 5
            #continue

        # In amenitiesMap if "SECURITY" is true, increase score by ten
        if apartment.get("amenitiesMap", {}).get("SECURITY", False):
            score += 5

        # If inactiveReason is not empty, remove it
        # if apartment.get("inactiveReason", ""):
        #    continue

        # if aea__ > NON_VEG_ALLOWED > display_value lowercase is no, remove it
        if apartment.get("aea__", {}).get("NON_VEG_ALLOWED", {}).get("display_value", "").lower() == "no":
            continue

        # if leaseType is "FAMILY" ignore it
        #if apartment.get("leaseType", "").lower() == "family":
        #    continue
        #else:
        #    score += 0

        # if leaseType is "BACHELOR_FEMALE", remove it
        if apartment.get("leaseType", "").lower() == "BACHELOR_FEMALE".lower():
            continue

        # if gym is true, increase score by 10
        #if apartment.get("amenitiesMap", {}).get("GYM", False):
        #    score += 5

        ## if lift is true, increase score by 10
        #if apartment.get("amenitiesMap", {}).get("LIFT", False):
        #    score += 1

        ## if pool is true, increase score by 10
        #if apartment.get("amenitiesMap", {}).get("POOL", False):
        #    score += 1

        #if apartment.get("buildingType", "").lower() == "ap":
        #    score += 5


        # Give better score for lower rent
        score += 10 - rent / 2000

        # Give better score for higher property size
        score += apartment.get("propertySize", 0) / 100

        # add score to apartment
        apartment.update({"score": score})

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
                "type": f"BHK{BHK}",
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
                    apartment["location"] = location
                    apartments[location].append(apartment)
    return apartments


def print_relevant_info(property_data):
    string = ""
    string += f"\nTitle: {property_data.get('propertyTitle')}"
    string += f"\nRent: ₹{property_data.get('rent')}"
    string += f"\nDeposit: ₹{property_data.get('formattedDeposit')}"
    string += f"\nSize: {property_data.get('propertySize')} sq.ft."
    string += f"\nLocation: {property_data.get('locality')}, {property_data.get('city')}"
    string += f"\nBathrooms: {property_data.get('bathroom')}"
    string += f"\nParking: {property_data.get('parkingDesc')}"
    string += f"\nFurnishing: {property_data.get('furnishingDesc')}"
    string += f"\nAvailable From: {property_data.get('availableFrom')}"
    string += f"\nProperty Type: {property_data.get('typeDesc')}"
    string += f"\nOwner: {property_data.get('ownerName')}"
    string += f"\nContacted: {'Yes' if property_data['contactedStatusDetails'].get('contacted') else 'No'}"
    string += f"\nURL: {property_data.get('detailUrl')}"
    string += f"\nActive: {property_data.get('active')}"
    string += f"\nLease Type: {', '.join(property_data.get('leaseTypeNew', []))}"
    string += "\n"
    return string

def main():
    apartments = getApartments()
    output = ""
    allAparments = []
    for location in apartments:
        allAparments += apartments[location]
    sortedApartments = sorted(allAparments, key=lambda x: x.get("score", 0), reverse=False)
        # output += f"{fullNames.get(location, location)}\n"
        # output += "=====\n"
        # sortedApartments = sorted(apartments[location], key=lambda x: x.get("score", 0), reverse=False)
    for apartment in sortedApartments:
            # output += f"{fullNames.get(location, location)}\n"
            output += f"{apartment.get('propertyTitle')},"
            maintenance = apartment.get("maintenance", 0)
            rent = apartment.get("rent", 0) - maintenance
            if not maintenance:
                output += f" ₹{apartment.get('rent')},"
            else:
                output += f" ₹{rent} + {maintenance} = {apartment.get('rent')},"

            # add property size
            activationDate = datetime.fromtimestamp(apartment.get('activationDate', 0)/1000).strftime('%B %d')
            apartment.get("activationDate", 0)
            output += f" {apartment.get('propertySize')} sqft, Deposit {apartment.get('deposit', 0)}, {activationDate}\n"
            output += f"{apartment.get('secondaryTitle')} - {apartment.get('location')}\n"

            # Create google maps https://maps.google.com/?q={apartment location} link from location
            # output += f"https://maps.google.com/?q={apartment.get('location')}\n"
            # output += f"{datetime.fromtimestamp(apartment.get('activationDate', 0)/1000).strftime('%B %d')} - {apartment.get('inactiveReason', '')}\n"
            # output += f"{apartment.get('buildingType')} {apartment.get('propertySize')}\n"
            output += f"{apartment.get('shortUrl')}\n"
            output += "---\n"
            # print(json.dumps(apartment, indent=2))
        # print(json.dumps(sortedApartments, indent=2))
    print(output)
    with open("output.txt", "a") as file:
        file.write(output)

    string = ""
    for property_data in sortedApartments:
        string += print_relevant_info(property_data)
    with open("/tmp/output.txt", "w") as file:
        file.write(string)

    # print(json.dumps(apartments, indent=2))


if __name__ == "__main__":
    main()
