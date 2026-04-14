# Centralized Network Ingress with Amazon API Gateway

This repository provides a **centralized network ingress layer** built on **Amazon API Gateway**, designed for highly available, multi-region AWS architectures. It enables secure, scalable, and resilient traffic routing across regions and accounts.

---

## 📖 Quick Overview

Think of this as a **global front door for your applications**. Instead of having a single entry point that goes down or gets slow, you have multiple entry points in different regions around the world. If one region has problems, traffic automatically gets sent to another region.

---

## Features & Capabilities

### 🌍 Multi-Region
- Deploy API Gateway endpoints across multiple AWS regions  
- Reduce latency and eliminate single-region failure scenarios  
- Support active/active or active/passive regional traffic patterns  

### 🛡 High Availability
- Leverages Amazon API Gateway’s fully managed, fault-tolerant service  
- No infrastructure management required  
- Automatically scales to meet traffic demand  

### 🌐 Dual-Stack (IPv4 & IPv6)
- Native support for both IPv4 and IPv6 clients  
- Ensures compatibility with modern and future network requirements  

### 🔁 Cross-Account Lambda Integration
- API Gateway can invoke Lambda functions across multiple AWS accounts  
- Enables strong account isolation and centralized ingress governance  
- Ideal for platform teams supporting multiple application teams  

### ❤️ Health Checks
- Continuous health checks for backend services  
- Automatically detects unhealthy regions or endpoints  
- Prevents routing traffic to failing components  

### 🔀 Route53 Failover
- Uses Amazon Route53 failover routing policies  
- Automatically redirects traffic during regional outages  
- Supports disaster recovery and business continuity objectives  

---

## Architecture Overview

The architecture consists of:
- **Amazon API Gateway** as the centralized ingress point  
- **AWS Lambda** backends deployed across multiple regions and accounts  
- **IAM cross-account permissions** for secure invocation  
- **Amazon Route53** for DNS-based routing and regional failover  
- **Health checks** to ensure traffic is sent only to healthy regions  

This approach provides a resilient, scalable, and enterprise-ready ingress solution for AWS workloads.

---

## Use Cases

- Centralized ingress for multi-account AWS environments  
- Global APIs requiring high availability and failover  
- Platform teams providing shared networking services  
- Disaster recovery and multi-region resilience strategies  

---

## API Endpoints

### Main Endpoints

| Region | Endpoint | Purpose |
|--------|----------|---------|
| **Primary** | `api.lukach.io` | Main API gateway — routes to the healthy region |
| **US East 1** | `use1.api.lukach.io` | Regional endpoint (N. Virginia) |
| **US West 2** | `usw2.api.lukach.io` | Regional endpoint (Oregon) |

### Available Routes

#### 1. Health Check
- **Endpoint:** `GET /health`
- **Purpose:** Check if the API is responding and see which region you're connected to
- **Response:** Returns the AWS region (e.g., `us-east-1`, `us-west-2`)
- **Example:**
  ```bash
  curl https://api.lukach.io/health
  ```

#### 2. Authorization/Authentication
The API includes built-in security through OAuth2 integration:
- All requests are validated through an authorization layer
- Users must provide an Authorization header with a valid OAuth2 token
- The authorizer verifies user information including email and account status

---

## Getting Started

### Prerequisites

- An AWS Account (with appropriate permissions)
- Python 3.13+
- AWS CDK CLI installed
- Git

### Installation & Deployment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jblukach/api.git
   cd api
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Deploy the infrastructure:**
   ```bash
   cdk deploy --all
   ```

4. **Verify deployment:**
   ```bash
   curl https://api.lukach.io/health
   ```

---

## 🔧 How It Works (In Plain English)

1. **Request comes in** → User sends a request to `api.lukach.io`
2. **Route53 checks health** → AWS checks if regions are healthy
3. **Smart routing** → Traffic goes to the closest healthy region
4. **Authentication check** → The API verifies you have permission
5. **Response sent back** → Your request gets processed and you get a response

If a region goes down, Route53 automatically sends traffic to another region without you having to do anything.

---

## Project Structure

```
api/
├── api/                    # API Gateway definitions for each region
│   ├── api_stack.py       # CI/CD permissions setup (GitHub Actions)
│   ├── api_use1.py        # US East 1 region configuration
│   └── api_usw2.py        # US West 2 region configuration
├── authorizer/            # Security/authentication logic
│   ├── authorizeruse1.py  # Authorization for US East 1
│   └── authorizerusw2.py  # Authorization for US West 2
├── health/                # Health check endpoint
│   └── health.py          # Returns current region status
├── app.py                 # Main CDK application
├── cdk.json              # Configuration file
└── requirements.txt       # Python dependencies
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **"Connection refused"** | The API might be down. Try another regional endpoint or wait a few moments. |
| **"Unauthorized" error** | Your OAuth2 token is invalid or expired. Please re-authenticate. |
| **"Slow response"** | You might be connecting to a distant region. Check which region is responding. |
| **Regional endpoint fails but main endpoint works** | That region is temporarily unhealthy. Traffic is being routed to another region. |

---

## Support & Questions

For issues, feature requests, or questions:
- Open an issue on [GitHub](https://github.com/jblukach/api/issues)
- Check the [AWS Documentation](https://docs.aws.amazon.com/apigateway/)
- Review AWS Route53 failover policies for advanced configurations

---
