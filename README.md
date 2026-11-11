# myapp · Kubernetes 微服务与云原生实践
> **👨‍💻 彭治皓** | 7年运维经验 | 专注云原生 | **求职意向：云原生运维 / K8s 运维工程师（深圳）**
> 
> 这是一个从零搭建的生产级 GitOps 闭环与可观测性平台，完整覆盖了从 K8s 集群初始化、微服务拆分、CI/CD 全自动交付到 Prometheus + Loki 监控告警的全链路实战。围绕 Kubernetes 集群部署、容器化应用和可观测性搭建的实践项目。仓库包含 Ansible 集群初始化脚本、基于 Flask 的示例服务、RabbitMQ 消息消费者，以及用于部署应用和基础设施组件的 Helm Chart。项目同时保留 Gitea Actions 构建流程，用于构建容器镜像并更新 Chart 中的镜像版本。

源码仓库：<https://github.com/Decade920/myapp>

## 🌟 核心亮点深度排障实战

*   **全链路 GitOps 自动化交付**：
    *   彻底分离 CI 与 CD：业务源码与 K8s 配置物理隔离。
    *   解决死循环：通过路径过滤与 `[skip ci]` 标签，完美解决 CI 机器人自动修改配置文件导致的无限触发问题。
    *   平滑更新：使用 `sed` 脚本精准替换 `values.yaml` 中的镜像 Tag，避免误伤其他微服务。
*   **全方位可观测性 (Metrics + Logs)**：
    *   基于 Operator 部署 `kube-prometheus-stack`，通过自定义 `ServiceMonitor` 实现业务指标（QPS）的自动发现。
    *   弃用旧版 Promtail，引入最新 **Grafana Alloy** 采集全集群日志，对接 **Loki 3.0** 存储。
*   **底层排障记录**：
    *   **全局日志爆红**：通过 LogQL 发现集群大量 `too many open files`，成功定位并修复宿主机 `fsnotify` 句柄耗尽与 `br_netfilter` 内核模块缺失问题。
    *   **网络瘫痪恢复**：排查并解决了旧版 Calico CNI Token 过期导致的 Pod 网络沙箱创建失败问题。
    *   **配置覆盖机制**：通过分析 Operator 控制器逻辑，成功解决 Alertmanager 告警配置被系统默认配置强制覆盖的痛点。
*   **安全合规 (Sealed Secrets)**：将加密后的数据库密码与镜像拉取凭证纳入 Git 仓库版本管理，保障机密信息零泄露。

## 项目结构

```text
.
├── .gitea/
│   └── workflows/          # Flask / Consumer 的 CI 工作流
├── ansible/
│   ├── playbooks/          # Kubernetes 集群初始化入口
│   └── roles/              # 节点、containerd、kubeadm、Master 等角色
├── apps/
│   ├── flask/              # Flask Web/API 服务
│   └── consumer/           # RabbitMQ 消息消费者
└── helm/
    ├── flask/              # Flask 应用及监控资源
    ├── consumer/           # 消息消费者
    ├── nginx/              # Nginx 入口与反向代理
    ├── mysql/              # MySQL StatefulSet
    ├── redis/              # Redis
    ├── rabbitmq/           # RabbitMQ StatefulSet
    └── monitoring/
        ├── alloy/          # Kubernetes 容器日志采集
        └── loki/           # Loki 日志存储
```

## 应用功能

### Flask 服务

`apps/flask/` 使用 Python 3.11 和 Flask 实现示例 Web 服务，并通过环境变量配置 Redis、MySQL 和 RabbitMQ 连接信息。

| 路由 | 功能 |
| --- | --- |
| `/` | 通过 Redis 自增计数，返回访问者序号 |
| `/db` | 向 MySQL 写入测试用户并返回用户总数 |
| `/send?msg=...` | 将消息发送到 RabbitMQ 的 `hello` 队列 |
| `/metrics` | 暴露 Prometheus 格式的 HTTP 请求指标 |

应用会在启动时尝试连接 Redis，并初始化 MySQL 的 `visits`、`users` 数据表。请求指标按 HTTP 方法和 endpoint 记录。

### RabbitMQ Consumer

`apps/consumer/` 是独立运行的消息消费者：

- 连接 RabbitMQ 的 `hello` 队列。
- 收到消息后输出消息内容。
- 使用手动确认（`auto_ack=False`），处理完成后调用 `basic_ack` 确认消息。

Flask 负责生产消息，Consumer 负责消费消息，二者通过 RabbitMQ 解耦。

## 基础设施与部署组件

### Kubernetes 集群初始化

`ansible/` 使用 Playbook 和 Role 组织集群初始化任务。当前 Playbook 的主要流程包括：

1. 初始化集群节点：关闭 swap、加载内核模块并设置网络转发参数。
2. 安装并配置 containerd，启用 systemd cgroup 驱动。
3. 安装 kubeadm、kubelet 和 kubectl，并锁定软件包版本。
4. 在 Master 节点执行 kubeadm init，配置 kubeconfig，并安装 Calico 网络插件。

当前 `ansible/playbooks/site.yml` 定义了 `k8s_cluster` 与 `k8s_master` 两组主机任务。执行前需要根据实际环境准备 Ansible inventory、SSH 访问和节点信息；仓库当前未包含 inventory 文件。Worker 加入集群的 Role 已单独提供，但尚未列入该入口 Playbook。

### Helm Charts

`helm/` 将应用和依赖服务拆分为独立 Chart，主要包括：

| Chart | 用途 |
| --- | --- |
| `flask` | Flask Deployment、Service、ConfigMap、Secret |
| `consumer` | RabbitMQ 消息消费者 Deployment |
| `nginx` | NodePort 入口、静态欢迎页及 Flask 反向代理 |
| `mysql` | MySQL StatefulSet 与持久化存储声明 |
| `redis` | Redis Deployment 与 Service |
| `rabbitmq` | RabbitMQ StatefulSet、AMQP 与管理端口 |
| `monitoring/alloy` | 发现 Kubernetes Pod 并采集容器日志 |
| `monitoring/loki` | Loki 日志存储，仓库提供单体部署配置 |

Flask Chart 还包含 ServiceMonitor、PrometheusRule 和 Grafana Dashboard ConfigMap，用于采集请求指标、定义告警规则并展示接口 QPS。

## CI/CD 流程

`.gitea/workflows/` 中提供两条 Gitea Actions 工作流：

- `flask-ci.yaml`：当 `apps/flask/**` 发生变更时构建 Flask 镜像并推送到腾讯云容器镜像仓库，然后更新 `helm/flask/values.yaml` 中的镜像 tag。
- `consumer-ci.yaml`：当 `apps/consumer/**` 发生变更时构建 Consumer 镜像并推送到镜像仓库，然后更新 `helm/consumer/values.yaml` 中的镜像 tag。

两条工作流也支持手动触发。运行前需要在 Gitea Actions 中配置工作流引用的 Secrets（例如 Git 仓库访问凭据和镜像仓库凭据），并按自己的环境调整仓库地址、镜像仓库命名空间及推送目标。

> 这两份工作流位于 `.gitea/workflows/`，属于 Gitea Actions 配置，不应与 GitHub Actions 工作流混淆。

## 本地运行应用

需要 Python 3.11 或兼容版本。

### 运行 Flask

```sh
cd apps/flask

python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

默认监听 `0.0.0.0:5000`。本地运行时请按实际环境设置 Redis、MySQL 和 RabbitMQ 的连接环境变量；默认服务地址面向 Kubernetes Service 命名，未启动依赖服务时，相关接口可能无法正常工作。

### 运行 Consumer

```sh
cd apps/consumer

python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python consumer.py
```

Consumer 默认连接主机名为 `rabbitmq-service` 的 RabbitMQ 服务，并监听 `hello` 队列。独立运行时请确保该主机名可解析，或根据实际环境调整连接配置。

## 配置与安全注意事项

- 部署前请检查各 Chart 的 `values.yaml`，按集群环境修改镜像地址、tag、命名空间、存储容量、拉取凭据和资源配置。
- 仓库中的部分示例配置包含默认数据库及 RabbitMQ 用户名、密码。它们仅适合本地实验，不应直接用于生产环境；请改用 Kubernetes Secret 或外部密钥管理，并避免将真实凭据提交到 Git。
- `helm/flask/values.yaml` 中的 Secret 示例会渲染到 Kubernetes 资源，不能将其视为安全的密钥存储方案。
- MySQL 和 RabbitMQ 使用 StatefulSet 与持久化卷声明；Redis 当前使用 hostPath 数据目录。部署前应确认节点磁盘、StorageClass 和备份策略符合预期。
- CI 工作流中包含特定 Gitea 地址和镜像仓库路径，迁移到其他环境时需要一并修改。
- 请勿将集群 kubeconfig、访问令牌、镜像仓库密码或生产数据库凭据放入公开仓库。

## 维护说明

- `apps/`：应用源代码与 Dockerfile。
- `ansible/`：Kubernetes 节点初始化、containerd、kubeadm 和 Master 配置。
- `helm/`：应用、数据服务与可观测性组件的 Helm Chart。
- `.gitea/workflows/`：应用镜像构建、推送和 Chart tag 更新流程。

本项目以 Kubernetes 部署实践为核心，涵盖应用容器化、服务发现、消息队列、持久化存储、指标监控与日志采集。具体部署参数应以目标集群和实际运行环境为准。

## 📫 联系我

![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![ArgoCD](https://img.shields.io/badge/ArgoCD-EF7B4D?style=for-the-badge&logo=argo&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=for-the-badge&logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=for-the-badge&logo=grafana&logoColor=white)
*   **姓名**：彭治皓
*   **电话**：15576264007
*   **邮箱**：424221714@qq.com
*   **期望城市**：北上广深杭川、长沙

*如果这个项目对你有启发，欢迎 Star ⭐*
