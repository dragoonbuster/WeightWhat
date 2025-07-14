# SizeComparator Frontend Assets

This directory contains the extracted frontend assets from the embedded HTML in the FastAPI application.

## Structure

```
frontend/
├── index.html          # Main HTML template
├── css/
│   ├── base.css        # Core styling and layout
│   └── components.css  # Component-specific styles
├── js/
│   ├── api-client.js   # API communication layer
│   └── app.js          # Main application logic
└── README.md           # This file
```

## Usage

### Serve Statically
```bash
# From the frontend directory
python3 -m http.server 3000

# Or using Node.js
npx serve .

# Access at http://localhost:3000
```

### Integration with Backend
The frontend expects the SizeComparator API to be available at the same origin or configured base URL.

API endpoints used:
- `POST /api/compare/fast` - Fast validated comparison
- `POST /api/compare/single` - Single AI call comparison
- `GET /health` - Health check
- `GET /api/performance` - Performance info

## Features

- **Fast Validated AI**: Sub-2 second response time with smart validation
- **Single Call Mode**: Alternative single AI provider mode
- **Responsive Design**: Mobile-first responsive layout
- **Interactive Examples**: Quick-access weight examples
- **Real-time Feedback**: Loading states and error handling
- **Modern Architecture**: Modular JavaScript with API abstraction

## Configuration

The frontend can be configured by modifying the SizeComparatorAPI constructor in `js/app.js` to point to a different backend URL if needed.

## Original Source

Extracted from: `src/api/fast_validated_mvp.py` (lines 58-390)