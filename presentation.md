# PostgreSQL Testing Dashboard Presentation

Jay Miller

- Founder Black Python Devs - <https://blackpythondevs.com>
- Staff Product Advocate - Aiven
  - Databases starting at $5
  - Free Tier Data Streaming (Apache Kafka)

---

## Why did I make this?

**Telemetry tells a story but not quickly**

- Elephant in the Room
- Jeff made something

---

## Why did I make this (_Professional Edition_)

- Database Ecosystem monitoring tools 👎
- Data is scattered across multiple regions and systems
- Performance patterns require manual correlation
- Quick insights are impossible manually with in distributed systems
- A unified view tells a story at a glance

---

## What makes this helpful

- Maps
- Charts
- AI

---

## Maps!

- Geographic distribution of databases affects performance
- Multiple latency patterns in one region are likely not YOUR PROBLEM
- Regional outliers and optimization opportunities surface

---

## Leaflet.js

**What is it and the quick add**

- Open-source JavaScript library for interactive maps
- Lightweight, mobile-friendly, and extensible
- Supports multiple tile layers and markers
- Quick integration: just include the CDN and create a map container
- Perfect for showing database locations and real-time health status

---

## Add leaflet.js

```html
 <!-- Make sure you put this AFTER Leaflet's CSS -->
 <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
     integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
     crossorigin=""></script>


 <div id="map"></div>
```
---

## Add points

```js
var map = L.map('map').setView([51.505, -0.09], 13);
var marker = L.marker([51.5, -0.09]).addTo(map);
```

more at <https://leafletjs.com/examples/quick-start/>

---

Database --> region --> lookup table --> Lat/Long

---


## Charts!

**Because Charts can tell you a lot quickly**

- Visual representations of time-series data
- Trends and anomalies become immediately obvious
- Compare performance across regions instantly
- Resource utilization patterns at a glance
- Make informed decisions based on visual data patterns

---

## Chart.js

**What it is and the quick add**

- Simple yet flexible JavaScript charting library
- 8 chart types out of the box (line, bar, pie, etc.)
- Responsive/High Def

more at <https://www.chartjs.org/docs/latest/getting-started/usage.html>

---

```html
# app/templates/base.html:    

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
```

---

```js
  <script>
    (function() {
      const chartId = '{{ chart_id }}';

      // Prepare data from server
      const queryData = {{ result.pg_stat_statements | tojson }};
```

---

```js
    // Generate labels (truncate queries for readability)
    const labels = queryData.map((q, i) => {
        const preview = q.query.replace(/\s+/g, ' ').substring(0, 30);
        return `Q${i+1}: ${preview}...`;
    });

    // Color palette
    const colors = [
        'rgba(255, 53, 84, 0.8)',   // Aiven red
        ...

    ];
```

---

 ```js
    const chartConfig = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          ...
          }
        },
        scales: {
          ...
        }
    };
    ```

---

```js
    // Calls Chart
    const callsCanvas = document.getElementById('callsChart_' + chartId);
```

---

```js
  if (callsCanvas) {
    new Chart(callsCanvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Number of Calls',
          data: queryData.map(q => q.calls),
          backgroundColor: colors,
        }]
      },
      options: chartConfig
    });
  }
```

---

- **Real-time updates**: Httpx
- **Historical analysis**: Time-series data with TimescaleDB
- **Correlation**: Link map locations with chart data
- **Scalability**: Handle multiple databases and concurrent users

---

## AI because it's 2025

- **Natural language queries**: Ask questions about your database health
- MCP: POSTGRESQL PRO - Query Optimization, (Not Implemented)

---


## Demo!
