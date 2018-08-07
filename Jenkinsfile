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
        stage('Wait for Travis CI results') {
            steps {
                script {
                    def commit = sh(script: "git rev-parse HEAD",
                                    returnStdout: true).trim()
                    def repo = 'release-engineering/resultsdb-updater'
                    def url = "https://api.travis-ci.org/repos/${repo}/builds"

                    def build = null

                    // try finding a Travis build for this commit for a minute or so
                    for (int i = 0; i < 4; i++) {
                        if (i > 0) { sleep(20) }

                        def response = sh(script: "curl -s ${url}",
                                          returnStdout: true).trim()
                        def json = new groovy.json.JsonSlurper().parseText(response)

                        for (b in json) {
                            if (b.commit.startsWith(commit)) {
                                build = b
                                break
                            }
                        }

                        if (build != null) { break }
                    }

                    if (build == null) {
                        error("No build found for commit ${commit}")
                    }

                    // wait for the build to finish for 15 minutes or so
                    for (int i = 0; i < 31; i++) {
                        if (build.state == 'finished') {
                            break
                        } else {
                            if (i > 0) { sleep(30) }

                            def response = sh(script: "curl -s ${url}/${build.id}",
                                              returnStdout: true).trim()
                            build = new groovy.json.JsonSlurper().parseText(response)
                        }
                    }

                    def build_url = "https://travis-ci.org/${repo}/builds/${build.id}"

                    if (build.state != 'finished') {
                        error("Travis CI build is taking too long: ${build_url}")
                    }

                    if (build.result != 0) {
                        error("Travis CI failed: ${build_url}")
                    }
                }
            }
        }

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
