#!/usr/bin/env bash
# shellcheck disable=SC2155
set -euo pipefail

readonly APP_NAME=go-trader
readonly IMAGE_TAG=${IMAGE_TAG:-latest}
readonly GIT_SHA=$(git rev-parse HEAD)
readonly ECR_URL="$(aws ecr get-authorization-token --output text --query 'authorizationData[].proxyEndpoint' | awk -Fhttps:// '{print $2}')"

parse_args() {

  usage=$(cat <<END
  Usage: build [OPTIONS]
  Options:
    -f  --file               Dockerfile name. Defaults to 'Dockerfile'. Optional
    -i  --image_name         Docker image name. Defaults to '${APP_NAME}'. Optional
    -n, --no-cache           Do not use cache when building the image. Optional
    -p, --push               Push the image to ECR. Defaults to 'false'. Optional
END
  )

  # Default values
  docker_file="Dockerfile"
  image_name=${APP_NAME}
  opts=
  push=true

  while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--file) docker_file=$2; shift; shift;;
        -i|--image_name) image_name=$2; shift; shift;;
        -n|--no-cache) opts="--no-cache"; shift;;
        -p|--push) push=true; shift;;
        *) echo "${usage}" && exit 1; shift;;
    esac
  done
}

login_ecr() {
  local login_status="$(aws ecr get-login-password | docker login -u AWS --password-stdin https://"${ECR_URL}")"
  echo "${login_status}"
  if [ "${login_status}" != "Login Succeeded" ]; then exit 1; fi
}

build_image() {
  echo "Building Dockerfile: ${image_name}"
  docker build ${opts} -t "${image_name}:${IMAGE_TAG}" -f "${docker_file}" .
}

push_image() {
  # Tag and push the image to ECR
  docker tag "${image_name}:${IMAGE_TAG}" "${ECR_URL}/${image_name}:${IMAGE_TAG}"
  docker push "${ECR_URL}/${image_name}:${IMAGE_TAG}"

  # Retag with git-sha: https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-retag.html
  local manifest=$(aws ecr batch-get-image --repository-name "${image_name}" --image-ids imageTag="${IMAGE_TAG}" --query 'images[].imageManifest' --output text)
  aws ecr put-image --repository-name "${image_name}" --image-tag "${GIT_SHA}" --image-manifest "${manifest}"

  echo "Successfully created and pushed the new Docker image"
  echo "${ECR_URL}/${image_name}:${IMAGE_TAG}"
}

main() {
  parse_args "$@"
  login_ecr
  build_image
  if [ "${push}" = true ]; then push_image; fi
}

main "$@"
