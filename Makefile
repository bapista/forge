.PHONY: help provision bootstrap diff lint
help:        ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n",$$1,$$2}'
provision:   ## Layer 1 — provision K3s on all nodes (Ansible)
	cd advanced/infra/ansible && ansible-playbook -i inventory.ini site.yml
bootstrap:   ## Layer 2 — install Argo CD + the root app-of-apps
	kubectl apply -k advanced/clusters/forge/bootstrap
	kubectl apply -f advanced/clusters/forge/root-app.yaml
diff:        ## Preview what GitOps would change for the demo workload
	kubectl diff -k advanced/workloads/podinfo || true
lint:        ## Render manifests client-side (what CI checks)
	kubectl apply --dry-run=client -k advanced/workloads/podinfo
