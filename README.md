# **NoDrums**

Welcome to **NoDrums**, the tool that intelligently removes drum sounds from audio tracks! Whether you're a musician, producer, or just an audio enthusiast, **NoDrums** helps you isolate melodies and harmonies by removing percussive elements from your tracks.

---

## **Features**
- Efficient drum sound removal from audio files.
- Easy to use via a web interface.
- Runs seamlessly in Docker or locally with Python.

---

## **Getting Started**

### **Run with Docker**
1. Clone the repository:
   ```bash
   git clone https://github.com/abutbul/NoDrums.git
   cd NoDrums
   ```
2. Build and run the Docker container:
   ```bash
   docker build -t nodrums .
   docker run --rm -p 5000:5000 nodrums
   ```
3. Access the app at `http://localhost:5000`.

### **Run Locally with Python Virtual Environment**
1. Clone the repository:
   ```bash
   git clone https://github.com/abutbul/NoDrums.git
   cd NoDrums
   ```
2. Set up a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Start the application:
   ```bash
   python app.py
   ```
4. Access the app at `http://localhost:5000`.

---

## **Contributing**
We welcome contributions! Check out the [contribution guidelines](https://github.com/abutbul/NoDrums/wiki/Contributing) to get started.

---

## **Further Details**
For more detailed instructions, troubleshooting, and advanced usage, visit our [wiki](https://github.com/abutbul/NoDrums/wiki).

---

**Enjoy making music your own!** 🎶
