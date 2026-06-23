.PHONY: help provision bootstrap diff lint
help:        ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'
provision:   ## Layer 1 — provision K3s on all nodes (Ansible)
	cd infra/ansible && ansible-playbook -i inventory.ini site.yml
bootstrap:   ## Layer 2 — install Argo CD + the root app-of-apps
	kubectl apply -k clusters/forge/bootstrap
	kubectl apply -f clusters/forge/apps/root-app.yaml
diff:        ## Show what GitOps would change
	kubectl diff -k apps/podinfo || true
lint:        ## Lint manifests
	kubectl apply --dry-run=client -k apps/podinfo
