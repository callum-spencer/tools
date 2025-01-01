import json
from tqdm import tqdm
from google.cloud import secretmanager
from googleapiclient.discovery import build

def list_projects():
    """Lists all GCP projects."""
    service = build('cloudresourcemanager', 'v1')
    request = service.projects().list()
    projects = []
    while request is not None:
        response = request.execute()
        for project in response.get('projects', []):
            projects.append({
                'projectId': project['projectId'],
                'name': project['name'],
                'lifecycleState': project['lifecycleState']
            })
        request = service.projects().list_next(previous_request=request, previous_response=response)
    return projects

def list_secrets_with_multiple_versions(project_id):
    """Lists secrets with multiple versions not in destroyed state."""
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project_id}"

    results = []
    secrets = client.list_secrets(request={"parent": parent})

    # Initialize progress bar
    secrets_list = list(secrets)  # Convert to a list for length calculation
    with tqdm(total=len(secrets_list), desc="Processing Secrets", unit="secret") as pbar:
        for secret in secrets_list:
            secret_name = secret.name
            versions = client.list_secret_versions(request={"parent": secret_name})
            active_versions = [
                version.name for version in versions 
                if version.state != secretmanager.SecretVersion.State.DESTROYED
            ]
            if len(active_versions) > 1:
                results.append({
                    "secret_name": secret_name,
                    "active_versions": len(active_versions),
                    "version_details": active_versions
                })
            pbar.update(1)  # Update the progress bar for each secret processed
    return results

def main():
    # Step 1: List all GCP projects
    print("Fetching GCP projects...")
    projects = list_projects()
    if not projects:
        print("No projects found.")
        return

    # Step 2: Display projects and allow user to select one
    print("\nAvailable Projects:")
    for idx, project in enumerate(projects):
        print(f"{idx + 1}. {project['name']} (ID: {project['projectId']}, State: {project['lifecycleState']})")
    
    selected_index = int(input("\nEnter the number of the project to select: ")) - 1
    if selected_index < 0 or selected_index >= len(projects):
        print("Invalid selection.")
        return

    selected_project = projects[selected_index]['projectId']
    print(f"\nSelected Project: {selected_project}")

    # Step 3: List secrets with multiple active versions
    print("\nScanning secrets for multiple active versions...")
    secrets_data = list_secrets_with_multiple_versions(selected_project)

    # Step 4: Save results to JSON file
    output_file = f"secrets_report_{selected_project}.json"
    with open(output_file, 'w') as f:
        json.dump(secrets_data, f, indent=4)

    print(f"\nScan complete. Results saved to {output_file}")

if __name__ == "__main__":
    main()