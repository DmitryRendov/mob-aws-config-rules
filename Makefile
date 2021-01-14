ifeq "$(CI)" "true"
	_AWSCLI_AUDIT_PROFILE :=
	_AWSCLI_PROD_PROFILE :=
else
	_AWSCLI_AUDIT_PROFILE := --profile audit-super-user
	_AWSCLI_PROD_PROFILE := --profile bastion-super-user
endif


deploy-%:
	$(eval _LAMBDA_FUNCTION_NAME := $(shell aws $(_AWSCLI_PROD_PROFILE) s3 cp s3://mob-terraform-state/audit/roles/aws-config - | jq -r '.modules[] | select(.path[] | contains("$*")) | .resources | select(."aws_lambda_function.default" != null) | ."aws_lambda_function.default".primary.attributes.function_name'))
	@rm -f $*.zip || true
	@zip -rj $*.zip $*
	@echo "Publishing new version (snapshotting) for function $(_LAMBDA_FUNCTION_NAME)"
	@echo "aws $(_AWSCLI_AUDIT_PROFILE) lambda publish-version --function-name $(_LAMBDA_FUNCTION_NAME)" || true
	@echo "Updating function code for $(_LAMBDA_FUNCTION_NAME)"
	@eecho "aws $(_AWSCLI_AUDIT_PROFILE) lambda update-function-code --function-name $(_LAMBDA_FUNCTION_NAME)" --zip-file fileb://$*.zip
	@echo "Deployed $(_LAMBDA_FUNCTION_NAME)"

logs-%:
	@awslogs  get /aws/lambda/audit-aws-config-$* ALL --watch --profile audit-super-user
