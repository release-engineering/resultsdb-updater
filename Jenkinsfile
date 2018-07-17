pipeline {
    agent {
        node {
            label 'docker'
        }
    }

    options {
        timestamps()
    }

    stages {
        stage('Build container image') {
            steps {
                script {
                    def appVersion = sh(returnStdout: true,
                                        script: './version.sh').trim()
                    def image = docker.build("factory2/resultsdb-updater:${appVersion}")
                    docker.withRegistry(params.REGISTRY, params.REGISTRY_AUTH_SECRET) {
                        image.push()
                    }
                }
            }
        }

        stage('Perform functional tests') {
            steps {
                echo 'TODO:'
                echo 'Deploy resultsdb...'
                echo 'Deploy message bus...'
                echo 'Deploy resultsdb-updater and connect it to the prev two'
                echo 'Run tests against the project'
            }
        }

        stage('Apply "latest" tag') {
            when {
                branch 'master'
            }
            steps {
                echo 'TODO'
            }
        }
    } // stages

    post {
        // This can be replaced with `fixed` and `regression`, once
        // Pipeline Model Definition Plugin version >= 1.2.8 is available.
        changed {
            script {
                if (ownership.job.ownershipEnabled) {
                    // if result hasn't been set to failure by this point, it's a success.
                    def currentResult = currentBuild.result ?: 'SUCCESS'
                    def previousResult = currentBuild.previousBuild?.result
                    def SUBJECT = ''

                    if (previousResult == 'FAILURE' && currentResult == 'SUCCESS') {
                        SUBJECT = "Jenkins job ${currentBuild.fullDisplayName} fixed."
                    }
                    else if (previousResult == 'SUCCESS' && currentResult == 'FAILURE' ) {
                        SUBJECT = "Jenkins job ${currentBuild.fullDisplayName} failed."
                    }

                    if (SUBJECT != '') {
                        emailext to: ownership.job.primaryOwnerEmail,
                                 subject: SUBJECT,
                                 body: "${currentBuild.absoluteUrl}"
                    }
                }
            } // script
        } // changed
    } // post
} // pipeline
