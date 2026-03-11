# AWS EC2 Launch Guide — AI Knowledge Platform

This guide provides the exact mouse-click steps to launch the recommended `t4g.large` instance on AWS for your AI Knowledge Platform.

---

## Step 1: Log in to AWS Console
1. Log in to [AWS Management Console](https://console.aws.amazon.com).
2. Ensure you are in your preferred region (e.g., **US East (N. Virginia) `us-east-1`**) in the top right corner.
3. Search for **EC2** in the top search bar and click it.

---

## Step 2: Initiate Instance Launch
1. On the EC2 Dashboard, click the orange **Launch instance** button.

---

## Step 3: Name and OS (AMI)
1. **Name:** Enter `AI-Knowledge-Platform`.
2. **Application and OS Images (AMI):** 
   * Select **Ubuntu**.
   * From the dropdown, choose **Ubuntu Server 24.04 LTS (HVM), SSD Volume Type**.
   * **IMPORTANT:** Ensure the Architecture dropdown is set to **64-bit (Arm)**. (This is required for the `t4g` instance family).

---

## Step 4: Instance Type
1. **Instance type:** Search for and select **`t4g.large`**.
   * *Required Specs:* 2 vCPU, 8 GiB Memory.

---

## Step 5: Key Pair (Login Credentials)
1. **Key pair name:** 
   * If you have an existing `.pem` or `.ppk` file, select it.
   * Otherwise, click **Create new key pair**. Give it a name (e.g., `ai-platform-key`), download the file, and keep it safe. You will need this to log in.

---

## Step 6: Network Settings (Firewall)
1. Click **Edit** on Network Settings.
2. **Security group name:** `ai-platform-sg-2026`.
3. **Inbound Security Group Rules:** You need to add 3 rules:

| Type | Port | Source | Description |
| :--- | :--- | :--- | :--- |
| **SSH** | `22` | **My IP** | Allows you to log into the terminal. |
| **Custom TCP**| `8000` | **Anywhere (0.0.0.0/0)** | Your Backend API. |
| **Custom TCP**| `8501` | **Anywhere (0.0.0.0/0)** | Your Streamlit Frontend UI. |

---

## Step 7: Storage (SSD)
1. **Configure Storage:** Change the size from 8 GiB to **50 GiB**.
2. **Volume Type:** Ensure **gp3** is selected (it is the fastest and cheapest).

---

## Step 8: Advanced Details (The Savings Pass)
1. Expand the **Advanced details** section at the bottom.
2. **Purchasing option:** Check the box for **Request Spot Instances**.
   * *This will reduce your price from ~$0.07/hr to ~$0.02/hr.*
3. Leave all other settings at their defaults.

---

## Step 9: Launch & Connect
1. Review the Summary pane on the right.
2. Click **Launch instance**.
3. Once the instance state says **Running**, copy the **Public IPv4 address**.
4. To log in from your terminal:
   ```bash
   chmod 400 your-key.pem
   ssh -i "your-key.pem" ubuntu@<your-public-ip-address>
   ```

---

## Step 10: Installation on the Server
Once you are logged into the server terminal, run these commands to start the platform:

```bash
# 1. Update and install Docker
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
# (Disconnect and reconnect for permission changes)

# 2. Setup Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2

# 3. Clone and Start
git clone https://github.com/1Touch-dev/AI-Documents-Analyser.git
cd AI-Documents-Analyser
# (Create your .env file)
docker compose up --build -d
```

Your platform will now be live at `http://<your-public-ip-address>:8501`.
