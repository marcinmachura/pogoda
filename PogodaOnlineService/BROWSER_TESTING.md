# Climate API Testing Guide

## Root Directory - Clean Structure

✅ **Only `test_api.py` remains in root** - Primary API testing script for both endpoints

## API Structure - Two Endpoints Only

The API now has a clean, focused structure with just two endpoints:
- `/api/v1/climate/aggregated` - Monthly climate averages with single classification
- `/api/v1/climate/yearly` - Individual year classifications only

# Manual Browser Testing Guide

## Starting the API Server

1. Open a terminal in the project directory (`c:\src\pogoda3`)
2. Run the server:
   ```bash
   python app/main.py
   ```
3. The server will start at: `http://127.0.0.1:8000`

## Interactive API Documentation (Swagger UI)

Visit: **http://127.0.0.1:8000/docs**

This provides a web interface where you can:
- See all available endpoints
- Test endpoints directly in the browser
- View request/response schemas
- Try different parameters

## Manual Testing with Two Endpoints

### 1. Aggregated Endpoint: `/api/v1/climate/aggregated` (POST)
**Purpose:** Returns monthly climate averages across all years with single classification

**Request Body:**
```json
{
  "city": "Paris",
  "years": [2018, 2019, 2020, 2021, 2022]
}
```

**Response:** Monthly averages and single classification
- `climate_data.avg_monthly_temps[]`: 12 monthly temperature averages
- `climate_data.avg_monthly_precip[]`: 12 monthly precipitation averages
- `climate_data.classification`: Single Köppen/Trewartha classification for the period

### 2. Yearly Endpoint: `/api/v1/climate/yearly` (POST)
**Purpose:** Returns only climate classifications for each year (no temp/precipitation data)

**Request Body:**
```json
{
  "city": "Berlin",
  "years": [2020, 2021]
}
```

**Response:** Year-to-classification mapping
- `yearly_data`: Object with year keys and Köppen/Trewartha classification values
- No temperature or precipitation data (classifications only)

## Using Browser Tools

### Option 1: Swagger UI (Recommended)
1. Go to `http://127.0.0.1:8000/docs`
2. Click on any endpoint to expand it
3. Click "Try it out"
4. Edit the request body
5. Click "Execute"
6. View the response below

### Option 2: Browser Developer Tools
1. Open browser developer tools (F12)
2. Go to Console tab
3. Use fetch API:

```javascript
// Test aggregated endpoint
fetch('http://127.0.0.1:8000/api/v1/climate/aggregated', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    city: "London",
    years: [2020, 2021]
  })
})
.then(response => response.json())
.then(data => console.log(data));

// Test yearly endpoint
fetch('http://127.0.0.1:8000/api/v1/climate/yearly', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    city: "Paris",
    years: [2020, 2021]
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

### Option 3: Postman or Similar Tools
- URL: `http://127.0.0.1:8000/api/v1/climate/aggregated` or `/yearly`
- Method: POST
- Headers: `Content-Type: application/json`
- Body: Raw JSON with city and years

## Testing Different Cities

The dataset covers specific regions. Try these cities:
- **London** (Europe)
- **Paris** (Europe) 
- **Berlin** (Germany)
- **Cape Town** (South Africa)
- **São Paulo** (Brazil)

## Expected Response Structures

### Aggregated Endpoint (`/api/v1/climate/aggregated`) Response:
```json
{
  "location": { ... },
  "start_year": 2020,
  "end_year": 2022,
  "distance_km": 0.41,
  "climate_data": {
    "avg_monthly_temps": [5.7, 8.0, 9.2, ...],  // 12 values
    "avg_monthly_precip": [56.3, 54.2, 35.8, ...],  // 12 values
    "classification": {
      "koppen_code": "Cfb",
      "koppen_name": "Oceanic",
      "trewartha_code": "Dfbl",
      "trewartha_name": "Dfbl"
    }
  }
}
```

### Yearly Endpoint (`/api/v1/climate/yearly`) Response:
```json
{
  "location": { ... },
  "start_year": 2020,
  "end_year": 2022,
  "distance_km": 4.98,
  "yearly_data": {
    "2020": {
      "koppen_code": "Csb",
      "koppen_name": "Mediterranean warm-summer",
      "trewartha_code": "Dsbl",
      "trewartha_name": "Dsbl"
    },
    "2021": { ... },
    "2022": { ... }
  }
}
```

## Troubleshooting

- **Server not starting:** Check if port 8000 is available
- **"City not found":** Try a different city name or check spelling
- **No climate data:** The city might be outside the dataset coverage area
- **Connection error:** Make sure the server is running on `http://127.0.0.1:8000`