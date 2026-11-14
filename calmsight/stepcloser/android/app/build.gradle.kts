import org.jetbrains.kotlin.gradle.dsl.JvmTarget
plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "fi.stepcloser.app"
    compileSdk = 36
    buildToolsVersion = "36.0.0"
    defaultConfig {
        applicationId = "fi.stepcloser.app"
        minSdk = 31
        targetSdk = 36
        versionCode = 6
        versionName = "0.5.0"
        ndk { abiFilters += "arm64-v8a" }
        manifestPlaceholders["mwdat_application_id"] = providers.gradleProperty("mwdat_application_id").orElse("0").get()
        manifestPlaceholders["mwdat_client_token"] = providers.gradleProperty("mwdat_client_token").orElse("0").get()
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    buildTypes { release { isMinifyEnabled = false } }
}
kotlin { compilerOptions { jvmTarget = JvmTarget.JVM_17 } }
dependencies {
    implementation("androidx.activity:activity-ktx:1.13.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.10.0")
    implementation("androidx.webkit:webkit:1.14.0")
    implementation("com.meta.wearable:mwdat-core:1.0.1")
    implementation("com.meta.wearable:mwdat-display:1.0.1")
    testImplementation("junit:junit:4.13.2")
}
