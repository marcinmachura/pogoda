# Logging Configuration

This application uses Python's built-in `logging` module for comprehensive logging.

## Log Levels

- **INFO**: Normal operation events (requests, responses, service initialization)
- **ERROR**: Error conditions (geocoding failures, data not found, server errors)  
- **DEBUG**: Detailed diagnostic information (data extraction details)

## Log Outputs

- **Console**: All logs are printed to stdout for development
- **File**: All logs are written to `logs/app.log` for persistence

## What Gets Logged

### API Requests
- All incoming HTTP requests with method and URL
- Request completion time and status code
- Request parameters (city, years)

### Business Logic
- Geocoding results and failures
- Climate model loading and closest location finding
- Data extraction success/failure
- Climate classification results

### Errors
- Geocoding errors with city name
- File not found errors for climate models
- Internal server errors with context

## Example Log Output

```
2025-09-13 10:30:15,123 - app.main - INFO - Application Climate API started successfully
2025-09-13 10:30:20,456 - app.main - INFO - Incoming request: POST http://127.0.0.1:8000/api/v1/climate/yearly
2025-09-13 10:30:20,457 - app.api.v1.routes.climate - INFO - Yearly climate data requested for London, years: [2020, 2021]
2025-09-13 10:30:20,458 - app.climate.service - INFO - Getting yearly climate data for London, years: [2020, 2021]
2025-09-13 10:30:20,459 - app.climate.service - INFO - Geocoded London to (51.5074456, -0.1277653)
2025-09-13 10:30:20,460 - app.climate.service - INFO - Loading climate model from data/models/climate_compact.pkl
2025-09-13 10:30:20,580 - app.climate.service - INFO - Found closest climate station at (51.5, -0.125), distance: 4.98km
2025-09-13 10:30:20,590 - app.climate.service - INFO - Successfully retrieved yearly data for London (distance: 4.98km)
2025-09-13 10:30:20,591 - app.main - INFO - Request completed: POST http://127.0.0.1:8000/api/v1/climate/yearly - Status: 200 - Time: 0.135s
```

## Configuration

Logging is configured in `app/main.py` with:
- Format: timestamp - logger_name - level - message
- Handlers: both file (logs/app.log) and console output
- Level: INFO (can be changed to DEBUG for more detail)

## Interview Tips

**Q: How would you implement logging in a production API?**

**A: I'd use structured logging with:**
1. **Built-in logging module** - Standard, reliable, no external dependencies
2. **Multiple outputs** - Console for development, files for production
3. **Appropriate levels** - INFO for normal operations, ERROR for issues, DEBUG for troubleshooting
4. **Request correlation** - Track requests from start to finish
5. **Context information** - Include relevant data (user input, processing time, error details)
6. **Log rotation** - Prevent log files from growing too large
7. **Centralized logging** - In microservices, aggregate logs to central system like ELK stack

**Key benefits:**
- **Debugging**: Trace issues through the entire request flow
- **Monitoring**: Track performance and error rates
- **Auditing**: Record what operations were performed
- **Security**: Log authentication attempts and suspicious activity