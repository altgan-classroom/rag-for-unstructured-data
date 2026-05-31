Here are the standard commands to install **Docker** on **Ubuntu** via the terminal:

---

### **Step 1: Update your system**

```bash
sudo apt update
sudo apt upgrade -y
```

---

### **Step 2: Install required packages**

```bash
sudo apt install apt-transport-https ca-certificates curl software-properties-common -y
```

---

### **Step 3: Add Docker's official GPG key**

```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
```

---

### **Step 4: Add the Docker repository**

```bash
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

---

### **Step 5: Update package index**

```bash
sudo apt update
```

---

### **Step 6: Install Docker**

```bash
sudo apt install docker-ce docker-ce-cli containerd.io -y
```

---

### **Step 7: Verify Docker installation**

```bash
sudo docker --version
```

---

### **Optional: Run Docker without `sudo`**

```bash
sudo usermod -aG docker $USER
newgrp docker
```


---

## ✅ **APT-based Docker Installation (Recommended for Production)**

**What it does:**

* Installs Docker directly from Docker's **official repository**.
* Gives you full control over Docker versions.
* Matches exactly how Docker intends its engine to run on Ubuntu.

**Advantages:**

* **Full feature support** — Works exactly as Docker documents.
* Supports advanced configurations (e.g., custom networking, storage drivers).
* Compatible with tools like `docker-compose` and `docker swarm`.
* Used widely in production environments.
* More flexibility for version control and updates.

**Disadvantages:**

* Slightly more setup steps.
* You need to manually add GPG keys and repositories.

So it is better to install using APT than with snap
---


