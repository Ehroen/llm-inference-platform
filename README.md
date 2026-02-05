Mise en place GitOps : GitHub ↔ ArgoCD ↔ Kubernetes (k3d)
Objectif

Mettre en place une chaîne GitOps où :

Git (GitHub) contient l’état désiré (manifests Kubernetes),

ArgoCD observe Git et réconcilie l’état désiré avec l’état réel,

Kubernetes orchestre l’exécution (pods/containers).

1) Initialiser un dépôt Git local (WSL Ubuntu)
Pourquoi

Git est la source de vérité (single source of truth) en GitOps.

Sans dépôt Git, ArgoCD n’a rien à observer.

Commandes (Ubuntu / WSL)

Créer un dossier projet dans le home Linux (meilleure perf/compat que /mnt/c/...) :

mkdir -p ~/llm-inference-platform
cd ~/llm-inference-platform
git init


Configurer l’identité Git (obligatoire pour committer) :

git config --global user.name "Matthieu Tang"
git config --global user.email "TON_EMAIL_GITHUB@exemple.com"

2) Créer une application Kubernetes minimale (YAML + Kustomize)
Pourquoi

Démontrer un déploiement complet GitOps avec une application simple.

Kustomize est supporté nativement par Kubernetes/ArgoCD et permet d’assembler plusieurs YAML.

Commandes (Ubuntu / WSL)

Créer l’arborescence :

mkdir -p apps/hello-kube


Créer un Deployment (pod) :

cat > apps/hello-kube/deployment.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-kube
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: hello-kube
  template:
    metadata:
      labels:
        app: hello-kube
    spec:
      containers:
        - name: hello
          image: hashicorp/http-echo:1.0.0
          args:
            - "-text=hello from argocd"
          ports:
            - containerPort: 5678
YAML


Créer un Service (exposition réseau) :

cat > apps/hello-kube/service.yaml <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: hello-kube
  namespace: default
spec:
  type: LoadBalancer
  selector:
    app: hello-kube
  ports:
    - name: http
      port: 80
      targetPort: 5678
YAML


Créer le fichier Kustomize (déclare les ressources à déployer) :

cat > apps/hello-kube/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
YAML

3) Committer l’application dans Git
Pourquoi

En GitOps, le commit est l’action (auditabilité, traçabilité, rollback).

ArgoCD va se baser sur la branche (ex: main) pour déployer.

Commandes (Ubuntu / WSL)
git add .
git commit -m "Add hello-kube app (kustomize)"


Standardiser la branche sur main :

git branch -M main

4) Mettre en place l’authentification GitHub via SSH (WSL)
Pourquoi

GitHub n’autorise plus l’auth par mot de passe pour git push en HTTPS.

SSH est le standard pro (stable, sans token à retaper, adapté GitOps).

Commandes (Ubuntu / WSL)

Générer une clé SSH :

ssh-keygen -t ed25519 -C "TON_EMAIL_GITHUB@exemple.com"


Démarrer l’agent SSH et ajouter la clé :

eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519


Afficher la clé publique à copier dans GitHub :

cat ~/.ssh/id_ed25519.pub


Action manuelle (GitHub UI) :

GitHub → Settings → SSH and GPG keys → New SSH key → coller la clé

Tester l’auth SSH :

ssh -T git@github.com


Résultat attendu :

“You’ve successfully authenticated…” (GitHub ne fournit pas de shell, c’est normal)

5) Créer le repository GitHub et pousser le code
Pourquoi

ArgoCD va lire l’état désiré depuis un repository distant.

On démarre en public pour éviter de gérer des credentials ArgoCD dès le début (on pourra rendre privé après).

Actions

Création du repo GitHub llm-inference-platform (UI GitHub)

Commandes (Ubuntu / WSL)

Définir le remote SSH :

git remote add origin git@github.com:Ehroen/llm-inference-platform.git


Pousser la branche main :

git push -u origin main


Vérifier que le remote est accessible :

git ls-remote origin

6) Déclarer l’application ArgoCD (lien ArgoCD → Git)
Pourquoi

ArgoCD ne “déploie” pas tout seul : il a besoin d’un objet Application qui lui dit :

quel repo observer,

quelle branche,

quel chemin,

quel namespace cible,

et la policy de synchronisation.

Commandes (Ubuntu / WSL)

Créer le dossier de config ArgoCD :

mkdir -p platform/argocd


Créer l’Application ArgoCD :

cat > platform/argocd/hello-kube-app.yaml <<'YAML'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: hello-kube
  namespace: argocd
spec:
  project: default
  source:
    repoURL: git@github.com:Ehroen/llm-inference-platform.git
    targetRevision: main
    path: apps/hello-kube
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
YAML


Explications des champs importants

repoURL/targetRevision/path : où se trouve l’état désiré

destination : cluster in-cluster + namespace cible

automated.prune=true : supprime les ressources retirées de Git

selfHeal=true : corrige automatiquement toute dérive manuelle (drift)

Commit/push de la définition ArgoCD (bonne pratique : tout dans Git) :

git add platform/argocd/hello-kube-app.yaml
git commit -m "Add ArgoCD Application for hello-kube"
git push


Bootstrap dans Kubernetes (une seule fois) :

kubectl apply -f platform/argocd/hello-kube-app.yaml

7) Vérification du déploiement GitOps
Pourquoi

Valider que la boucle GitOps fonctionne :

ArgoCD observe Git

ArgoCD applique au cluster

Kubernetes crée les pods/services

Commandes (Ubuntu / WSL)

Vérifier l’objet Application :

kubectl get applications -n argocd


Vérifier les ressources Kubernetes créées :

kubectl get deploy,svc,pods -l app=hello-kube


Tester l’accès HTTP via le port exposé par k3d (si cluster créé avec --port "8080:80@loadbalancer") :

curl -s http://localhost:8080


Résultat attendu :

hello from argocd

Résultat / conclusion (à mettre dans ton rapport)

À ce stade, une chaîne GitOps complète est opérationnelle :

GitHub contient les manifests (état désiré)

ArgoCD (dans le namespace argocd) observe la branche main et le path apps/hello-kube

Kubernetes (k3d) applique et maintient les ressources (Deployment + Service)

La politique selfHeal assure la correction automatique de drift, et prune assure la suppression des ressources supprimées de Git.
