# Provisioning Helm Chart for OpenShift

## Contents

- Deployment
- Service
- OpenShift Route
- ConfigMap
- ServiceAccount
- External Git Secret support
- Readiness/Liveness probes
- Resources

## 1. Configure image

Edit `values.yaml`:

```yaml
image:
  repository: <INTERNAL_REGISTRY>/a0556722346-dev/provisioning
  tag: "1.0"
  pullPolicy: IfNotPresent
```

## 2. Configure Git repositories

Edit:

```yaml
config:
  git:
    namespaceRepo: "https://YOUR-GIT-SERVER/cluster-registry.git"
    monitoringRepo: "https://YOUR-GIT-SERVER/monitoring-registry.git"
    argocdRepo: "https://YOUR-GIT-SERVER/argocd-registry.git"
```

If the OpenShift environment is air-gapped, these URLs must point to repositories reachable from the cluster.

## 3. Create Git credentials

Do not commit credentials to Git or values.yaml.

```bash
oc create secret generic provisioning-git \
  --from-literal=GIT_USERNAME="YOUR_USERNAME" \
  --from-literal=GIT_TOKEN="YOUR_TOKEN"
```

The chart references this existing Secret by default:

```yaml
secret:
  existingSecret: provisioning-git
```

## 4. Validate

```bash
helm lint .
helm template provisioning .
```

## 5. Install

```bash
oc project a0556722346-dev
helm install provisioning .
```

## 6. Check

```bash
helm list
oc get pods
oc get svc
oc get route
oc logs deployment/provisioning
```

## 7. Upgrade

```bash
helm upgrade provisioning . --set image.tag=1.1
```

## 8. Uninstall

```bash
helm uninstall provisioning
```

## Important

The chart deploys the application. It does not provide network access to GitHub/GitLab. The OpenShift cluster must be able to reach the Git server used by the provisioning application.
