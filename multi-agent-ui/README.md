# Multi-Agent UI - React Frontend

A modern, responsive React-based user interface for the Multi-Agent Analytics System. This UI provides a chat-like interface for querying AppsFlyer click data using natural language.

## Features

✅ **Real-time Streaming** - Server-Sent Events (SSE) for live response streaming
✅ **Bilingual Support** - Automatic RTL/LTR direction for Hebrew and English
✅ **Chart Rendering** - Automatic visualization of data with ChartRenderer
✅ **Table Rendering** - Formatted tables with TableRenderer component
✅ **Conversation History** - LocalStorage persistence across sessions
✅ **Multiple Chats** - Create and manage multiple conversation threads
✅ **Debug View** - Optional debug panel showing pipeline execution traces
✅ **Modern Design** - Tailwind CSS with dark theme and smooth animations

## Tech Stack

- **React 18** - UI framework
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Server-Sent Events (SSE)** - Real-time communication
- **LocalStorage** - Client-side persistence

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The UI will be available at `http://localhost:5173`

## Project Structure

```
multi-agent-ui/
├── src/
│   ├── App.jsx                    # Main application component
│   ├── main.jsx                   # Entry point
│   ├── index.css                  # Global styles
│   ├── components/
│   │   └── renderers/
│   │       ├── ChartRenderer.tsx  # Chart visualization component
│   │       └── TableRenderer.tsx  # Table formatting component
│   └── lib/
│       ├── adkClient.js          # ADK backend communication
│       └── mockApi.js            # Utility functions
├── public/                        # Static assets
├── index.html                     # HTML template
├── vite.config.js                # Vite configuration
├── tailwind.config.js            # Tailwind CSS configuration
└── package.json                   # Dependencies
```

## Components

### App.jsx
Main application component managing:
- Conversation state and history
- Multiple chat sessions
- Message sending and receiving
- SSE connection handling
- LocalStorage persistence

### ChartRenderer.tsx
Renders chart visualizations from agent responses:
- Displays base64-encoded PNG images
- Responsive sizing
- Error handling

### TableRenderer.tsx
Renders structured data tables:
- Parses Markdown table format
- Responsive design
- Top finding highlights
- RTL/LTR text direction support

### adkClient.js
Backend communication layer:
- `createSession()` - Initialize ADK session
- `sendMessageSSE()` - Send messages via SSE
- Automatic reconnection
- Error handling

## Features in Detail

### Multi-turn Conversations
- Each chat maintains its own conversation history
- Context is preserved across turns
- Previous messages are displayed in chat bubbles

### Language Support
- Automatic detection of Hebrew vs English
- RTL (Right-to-Left) support for Hebrew
- LTR (Left-to-Right) support for English
- Mixed language support in same conversation

### Chart Visualization
When the backend returns `render_type="chart"`:
- ChartRenderer displays the chart image
- Charts are embedded as base64 PNG data URIs
- Responsive sizing for different screen sizes

### Table Display
When the backend returns `render_type="table"`:
- TableRenderer parses Markdown table format
- Responsive table design with horizontal scroll
- Alternating row colors for readability
- Top finding highlighting

### Debug Panel
Toggle debug view to see:
- Pipeline execution stages
- Agent routing decisions
- Cache hit/miss status
- Error traces

### LocalStorage Persistence
- Conversations stored in `multi_agent_ui_convos_v1`
- Active chat ID in `multi_agent_ui_active_id_v1`
- Survives page refreshes
- "Clear History" button to reset

## Configuration

### Backend URL
Update in `src/lib/adkClient.js`:
```javascript
const BASE_URL = "http://localhost:8080";
```

### Styling
Customize theme in `tailwind.config.js`:
```javascript
theme: {
  extend: {
    colors: {
      // Add custom colors
    }
  }
}
```

## Development

### Hot Module Replacement (HMR)
Changes to source files auto-reload in browser during development:
```bash
npm run dev
```

### Building for Production
```bash
# Create optimized production build
npm run build

# Output in dist/ folder
```

### Code Quality
```bash
# Run ESLint
npm run lint
```

## Example Usage

1. **Ask a Question**
   ```
   How many clicks for app_id_20 on 2025-10-24?
   ```

2. **Request a Chart**
   ```
   Show me a chart of clicks by media source
   ```

3. **Ask for Anomalies**
   ```
   Show me anomalies for facebook
   ```

4. **Hebrew Support**
   ```
   כמה קליקים היו אתמול?
   ```

## Troubleshooting

### Backend Connection Issues
- Ensure backend is running: `adk web --log_level debug`
- Check backend URL in `adkClient.js`
- Verify CORS settings if running on different ports

### LocalStorage Issues
- Clear browser cache and reload
- Use "Clear History" button in UI
- Check browser console for errors

### Chart Not Displaying
- Verify backend returns `render_type="chart"`
- Check `chart_image` contains valid base64 data URI
- Inspect browser console for rendering errors

### Hebrew Text Issues
- Ensure proper UTF-8 encoding
- Check that RTL direction is applied
- Verify font supports Hebrew characters

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance

- Lazy loading for large chat histories
- Automatic cleanup of old messages
- Optimized re-renders with React.memo
- Efficient SSE connection management

## Contributing

See main project [SPECIFICATION.md](../SPECIFICATION.md) for overall architecture.

### Adding New Renderers
1. Create component in `src/components/renderers/`
2. Handle specific `render_type` from backend
3. Import and use in `App.jsx`

### Styling Guidelines
- Use Tailwind utility classes
- Follow existing color scheme
- Ensure RTL/LTR compatibility
- Test on mobile devices

## License

Internal project for AppsFlyer analytics.
