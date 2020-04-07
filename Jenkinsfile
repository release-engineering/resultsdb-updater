/*
Although the pipeline below doesn't define any parameters, it will expect
the job running it to provide some:

    SPEC_URL              URL to resultsdb-updater spec file.
    REGISTRY              URL of the registry where the resultsdb-updater image
                          is going to be pushed.
    REGISTRY_AUTH_SECRET  Name of the secret stored as a Jenkins credential to
                          be used to authenticate to the registry.
*/
pipeline {
    agent any
    options {
        timestamps()
    }

    stages {
        stage('Run unit tests') {
            agent {
                node {
                    label 'fedora-28'
                }
            }
            environment {
                SPEC_FILE = 'resultsdb-updater.spec'
            }
            steps {
                sh '''
                curl  $SPEC_URL > $SPEC_FILE
                sudo dnf -y builddep $SPEC_FILE
                # This works because the spec file is only for the python2 package
                sudo dnf -y install $(awk '/^Requires: / {printf $2" "}' $SPEC_FILE)
                sudo dnf -y install python3-flake8 python2-pytest python2-requests-mock
                '''

                sh 'flake8 --ignore E731 --exclude .tox,.git'

                sh 'pytest -vv'
            }
        }
        stage('Build container image') {
            agent {
                node {
                    label 'docker'
                }
            }
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
            agent {
                node {
                    label 'fedora-28'
                }
            }
            steps {
                echo 'TODO:'
                echo 'Deploy resultsdb...'
                echo 'Deploy message bus...'
                echo 'Deploy resultsdb-updater and connect it to the prev two'
                echo 'Run tests against the project'
            }
        }

        stage('Apply "latest" tag') {
            agent {
                node {
                    label 'fedora-28'
                }
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
