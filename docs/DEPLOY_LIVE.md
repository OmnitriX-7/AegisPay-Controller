# 🚀 Live Cloud Deployment Guide: AegisPay-Controller

To provide hackathon judges with a live interactive public URL (e.g. `https://aegispay-controller.onrender.com`), you can deploy this repository directly using free cloud tiers on **Render**, **Railway**, or **Hugging Face Spaces**.

---

## ⚡ Method 1: Deploy on Render (Recommended & 100% Free)

Render automatically detects our root [`render.yaml`](../render.yaml) and [`Dockerfile`](../Dockerfile).

### Steps:
1. **Push your code to GitHub**:
   Ensure your latest commits are pushed to your GitHub repository:
   ```bash
   git add .
   git commit -m "feat: grand prize winning reconciliation platform"
   git push origin main
   ```
2. **Open Render**:
   Go to **[dashboard.render.com](https://dashboard.render.com)** and sign in with your GitHub account.
3. **Create New Blueprint**:
   * Click **New +** &rarr; **Blueprint**
   * Connect your `Razorpay-Buildathon` repository.
   * Render will automatically parse `render.yaml` and configure the web service with Docker.
4. **Set Environment Variables**:
   * Add `GEMINI_API_KEY` (Your Google Gemini API Key from Google AI Studio).
   * (Optional) Add `RAZORPAY_WEBHOOK_SECRET`.
5. **Click "Apply"**:
   Render will build the Docker container and deploy your live URL (e.g. `https://aegispay-controller.onrender.com`) within ~2 minutes!

---

## ⚡ Method 2: Deploy on Railway

1. Go to **[railway.app](https://railway.app/)**.
2. Click **New Project** &rarr; **Deploy from GitHub repo**.
3. Select your `Razorpay-Buildathon` repository.
4. Railway will automatically build using the existing [`Dockerfile`](../Dockerfile).
5. In **Settings &rarr; Networking**, click **Generate Domain**.
6. In **Variables**, add:
   * `PORT` = `8000`
   * `GEMINI_API_KEY` = `<your-gemini-key>`

---

## ⚡ Method 3: Deploy on Hugging Face Docker Spaces (Free 16GB RAM)

1. Go to **[huggingface.co/spaces](https://huggingface.co/spaces)**.
2. Click **Create new Space**:
   * License: `MIT`
   * Space SDK: **Docker** &rarr; Blank
3. Clone the Space repo or push this codebase to your Space remote:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/aegispay-controller
   git push space main
   ```
4. In Space **Settings &rarr; Variables and secrets**, add `GEMINI_API_KEY`.
5. Your Space will build and launch with a persistent public URL!

---

## 📋 What Judges Can Access on Your Live Link:

* 🌐 **Live Web Application**: `https://<your-app-url>/`
* 🔍 **API Health & Invariant Proof**: `https://<your-app-url>/api/status`
* 📊 **Live Prometheus Metrics**: `https://<your-app-url>/metrics`
* 📑 **Interactive Swagger API Docs**: `https://<your-app-url>/docs`
* 📂 **Custom Datasheet Ingestion**: Judges can upload custom CSVs or click **1-Click Load Sample Datasheets**.
* 🧠 **CFO Copilot**: Generative AI dispute recovery letters, Form 26AS audit, and cash runway simulations.
