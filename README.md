# LogiTrack - Smart Logistics & Shipment Management System

LogiTrack is a comprehensive, full-stack logistics management platform engineered with Python, Flask, SQLite / SQLAlchemy, and Bootstrap 5. It manages end-to-end supply chain operations, freight booking, linehaul containerization, driver route tracking, delivery verification, and electronic signatures.

---

## 🌟 Key Features

### 1. Multi-Role User Portals
- **Administrator**: Fleet overview, revenue analytics, driver assignments, and branch metrics.
- **Branch Manager**: Linehaul multi-order container dispatch, driver assignments, freight handling, and physical cash settlement.
- **Driver / Courier**: Active container transport runs, last-mile individual order routing, touch-enabled electronic receiver signature pad, and cash collection.
- **Customer**: Dynamic shipping cost calculation with categorized item rates, interactive parcel booking, Leaflet map route tracking, invoice downloads, and digital payment simulation (UPI QR Code / Card).

### 2. Live Shipment Tracking & Route Visualization
- Interactive OpenStreetMap / Leaflet map with multi-stop transit nodes.
- Real-time status indicators (Booked, Confirmed, In-Transit, Out for Delivery, Delivered).
- Dynamic ETA estimation based on transit speed and route distance.

### 3. Responsive & Modern Interface
- Full laptop, tablet, and smartphone optimization.
- Slide-over mobile drawer sidebar navigation.
- Bottom quick-navigation bar tailored for mobile devices.
- Dark / Light mode toggle with persistent local preferences.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- pip

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd logitrack
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize database and seed demo data**:
   ```bash
   python seed.py
   ```

4. **Start the application**:
   ```bash
   python run.py
   ```
   Open `http://127.0.0.1:5000` in your web browser.

---

## 🔑 Demo Seed Credentials

| Role | Username | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` |
| **Branch Manager** | `Mumbai_Manager01` | `Mumbai@2022` |
| **Driver** | `Mum_driver01` | `Mumbai@2022` |
| **Customer** | `Samithbshettigar` | `Samith@2022` |

---

## 📄 License
This project is licensed under the MIT License.
