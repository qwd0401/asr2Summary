# 🚀 MeetAssistant - Intelligent Meeting Assistant

A Flask-based intelligent meeting assistant system that provides speech-to-text, meeting summarization, and data management capabilities. Supports professional summary templates for various meeting types, making meeting records more efficient and professional.

## ✨ Core Features

### 🎤 Audio Processing
- **Multi-format Support**: Supports mainstream audio formats including MP3, WAV, M4A, FLAC
- **High-precision Transcription**: Based on advanced speech recognition technology for accurate speech-to-text conversion
- **Large File Processing**: Supports audio file uploads up to 100MB
- **Real-time Progress**: Provides real-time progress feedback during processing

### 📝 Intelligent Summarization
- **Multi-template Support**: Built-in 8 professional meeting templates
  - 🏢 **Product Meetings**: Product planning, requirement discussions, feature reviews
  - 🤝 **Business Meetings**: Business negotiations, partnership discussions, sales meetings
  - 🔧 **Technical Meetings**: Technical reviews, architecture design, code reviews
  - 👥 **Management Meetings**: Team management, project management, strategic planning
  - 📈 **Marketing Meetings**: Marketing strategies, campaigns, brand promotion
  - 💰 **Finance Meetings**: Financial analysis, budget planning, cost control
  - 🧪 **Test Case Reviews**: Test case reviews, testing strategy development
  - 📋 **Requirement Reviews**: Requirement analysis, requirement change discussions
  - 📄 **General Meetings**: Suitable for various general meeting scenarios

- **Structured Output**: Generates structured content including topics, decisions, task lists, risk identification
- **Professional Terminology**: Uses appropriate professional terms and expressions for different meeting types

### 🌐 Web Interface
- **Intuitive Operation**: Drag-and-drop upload, one-click processing, real-time feedback
- **Unified Dashboard**: Integrated usage statistics and database management features
- **Responsive Design**: Supports desktop and mobile device access
- **File Management**: Automatically saves processing results, supports batch downloads

### 📊 Data Statistics
- **Usage Analysis**: Detailed API call statistics and performance metrics
- **Error Monitoring**: Real-time error tracking and logging
- **Visual Charts**: Intuitive data display and trend analysis

### 🗄️ Data Management
- **SQLite Database**: Lightweight data storage solution
- **Data Backup**: Supports database backup and recovery
- **Management Interface**: Provides complete database management functionality

## 🛠️ Technology Stack

- **Backend Framework**: Flask 2.3.3
- **Database**: SQLite
- **Frontend**: HTML5 + CSS3 + JavaScript
- **Chart Library**: Chart.js
- **HTTP Client**: Requests 2.31.0
- **Web Server**: Werkzeug 2.3.7

## 📦 Quick Start

### System Requirements
- Python 3.8+
- At least 2GB RAM
- At least 10GB disk space

### Installation Steps

1. **Clone Project**
   ```bash
   git clone <repository-url>
   cd meetassistant
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Service**
   ```bash
   python app.py
   ```

4. **Access Application**
   - Homepage: http://localhost:5000
   - Unified Dashboard: http://localhost:5000/unified_dashboard
   - API Documentation: See [API_README.md](API_README.md)

## 🎯 User Guide

### Web Interface Usage

1. **Upload Audio Files**
   - Visit homepage http://localhost:5000
   - Drag audio files to upload area or click to select files
   - Supported formats: MP3, WAV, M4A, FLAC, etc.

2. **Process Audio**
   - Click "Start Processing" button
   - System will automatically complete speech transcription and meeting summarization
   - Can click "Cancel Processing" to interrupt task at any time

3. **View Results**
   - View transcription text and meeting summary online after processing
   - Support downloading generated files (.txt and .md formats)

4. **Data Statistics**
   - Click "📊 View Usage Statistics" to access unified dashboard
   - View detailed usage data and performance metrics
   - Manage database and system settings

### API Calls

For detailed API documentation, please refer to [API_README.md](API_README.md), including:
- File upload interface
- Speech transcription interface
- Meeting summarization interface
- One-click processing interface
- Statistics data interface

## 📁 Project Structure

```
meetassistant/
├── app.py                 # Main application
├── app_db.py             # Database management application
├── asr2text.py           # Speech-to-text module
├── meetassistant.py      # Core processing logic
├── database.py           # Database operations
├── compression_utils.py  # File compression utilities
├── templates/            # HTML templates
│   ├── index.html        # Homepage
│   ├── dashboard.html    # Management dashboard
│   └── unified_dashboard.html # Unified dashboard
├── templates_config.json # Meeting template configuration
├── uploads/              # Upload files directory
├── summaries/            # Processing results directory
├── logs/                 # Log files directory
├── requirements.txt      # Python dependencies
├── API_README.md         # API documentation
├── DEPLOYMENT.md         # Deployment guide
└── README.md            # Project documentation
```

## 🚀 Deployment Guide

### Development Environment
```bash
# Start development server
python app.py
```

### Production Environment
For detailed production environment deployment guide, please refer to [DEPLOYMENT.md](DEPLOYMENT.md), including:
- Traditional deployment methods
- Docker containerized deployment
- Nginx reverse proxy configuration
- System service configuration

### Docker Deployment
```bash
# Build image
docker build -t meetassistant .

# Run container
docker run -p 5000:5000 meetassistant

# Or use docker-compose
docker-compose up -d
```

## 📊 Feature Highlights

### 🎯 Professional Templates
- Customized professional templates for different industries and meeting types
- Structured output format for easy subsequent processing and archiving
- Support for custom template extensions

### 📈 Data Insights
- Real-time usage statistics and performance monitoring
- Error tracking and log analysis
- Visual data presentation

### 🔧 Easy Integration
- RESTful API design for easy third-party integration
- Complete API documentation and sample code
- Support for batch processing and automated workflows

## 🤝 Contributing

Welcome to submit Issues and Pull Requests to help improve the project!

1. Fork the project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support & Feedback

If you encounter problems during use or have suggestions for improvement, please:
- Submit [Issue](../../issues)
- Send email to project maintainers
- Check [API Documentation](API_README.md) and [Deployment Guide](DEPLOYMENT.md)

---

**MeetAssistant** - Making meeting records smarter and work more efficient! 🚀
