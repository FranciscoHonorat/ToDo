resource "kind_cluster" "todo" {
  name           = "todo"
  wait_for_ready = true
}

resource "terraform_data" "images" {
  triggers_replace = [kind_cluster.todo.id]

  provisioner "local-exec" {
    command = "kind load docker-image todo-backend:local todo-frontend:local --name ${kind_cluster.todo.name}"
  }
}

provider "helm" {
  kubernetes = {
    config_path = kind_cluster.todo.kubeconfig_path
  }
}

resource "helm_release" "todo" {
  name             = "todo"
  chart            = "${path.module}/../helm/todo"
  namespace        = "todo"
  create_namespace = true
  wait             = true

  depends_on = [terraform_data.images]
}