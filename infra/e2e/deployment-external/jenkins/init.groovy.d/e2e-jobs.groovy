import hudson.model.FreeStyleProject
import hudson.model.ParametersDefinitionProperty
import hudson.model.StringParameterDefinition
import hudson.security.csrf.GlobalCrumbIssuerConfiguration
import hudson.tasks.Shell
import jenkins.model.Jenkins

def instance = Jenkins.get()
GlobalCrumbIssuerConfiguration.DISABLE_CSRF_PROTECTION = true
["e2e-deploy", "e2e-rollback", "e2e-verify"].each { name ->
  if (instance.getItem(name) != null) {
    return
  }
  def job = instance.createProject(FreeStyleProject, name)
  job.addProperty(new ParametersDefinitionProperty([
    new StringParameterDefinition("DEPLOY_ENV", "test", "Target environment"),
    new StringParameterDefinition("RELEASE_ID", "e2e", "Release identifier"),
  ]))
  job.buildersList.add(new Shell("echo ${name} \$DEPLOY_ENV \$RELEASE_ID"))
  job.save()
}
