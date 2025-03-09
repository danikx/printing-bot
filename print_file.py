import os
import subprocess

def print_file(file_path, printer_name=None, page=None):
    """
    Print a file using lpr command
    Args:
        file_path: Path to the file to print
        printer_name: Name of the printer (optional)
        page: Page number to print (optional)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Build the lpr command
    command = ['lpr']
    if printer_name:
        command.extend(['-P', printer_name])
    if page:
        command.extend(['-o', f'page-ranges={page}'])
    command.append(file_path)
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("Print result :", result.stdout)
        print(f"Successfully sent {file_path} to printer")


        # Check queue for our job
        queue_cmd = ['lpq']
        if printer_name:
            queue_cmd.extend(['-P', printer_name])
        
        queue_result = subprocess.run(queue_cmd, capture_output=True, text=True, check=True)
        
        # Parse queue output to find our job
        for line in queue_result.stdout.split('\n'):
            if file_path in line:  # Find line containing our file name
                parts = line.split()
                if len(parts) >= 1:
                    job_id = parts[2]
                    print(f"Job ID: {job_id}")
                    return job_id
        return None
    except subprocess.CalledProcessError as e:
        print(f"Error printing file: {e}")

def get_printer_queue(printer_name=None):
    """
    Check printer queue using lpq command
    Args:
        printer_name: Name of the printer (optional)
    """
    command = ['lpq']
    if printer_name:
        command.extend(['-P', printer_name])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("Printer Queue:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error checking printer queue: {e}")

def get_printer_status(printer_name=None):
    """
    Check printer status using lpstat command
    Args:
        printer_name: Name of the printer (optional)
    Returns:
        bool: True if printer is online, False if offline or not found
    """
    command = ['lpstat', '-p']
    if printer_name:
        command.append(printer_name)
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if printer_name:
            print("Priter status : ", result.stdout)
            # Check specific printer status
            return "enabled" in result.stdout.lower()
        else:
            # Print status of all printers
            print("Printers Status:")
            print(result.stdout)
            return True
    except subprocess.CalledProcessError as e:
        print(f"Error checking printer status: {e}")
        return False

def remove_print_job(job_id=None, printer_name=None):
    """
    Remove print jobs from queue using lprm command
    Args:
        job_id: ID of the job to remove (optional, removes all jobs if None)
        printer_name: Name of the printer (optional)
    """
    command = ['lprm']
    if printer_name:
        command.extend(['-P', printer_name])
    if job_id:
        command.append(str(job_id))
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("Remove job result:", result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error removing print job: {e}")

# Update the main section to include status check
if __name__ == "__main__":
    printer_name = "Canon_LBP3010_LBP3018_LBP3050"
    
    print(get_printer_status(printer_name))

    get_printer_queue(printer_name)

    remove_print_job(printer_name=printer_name, job_id='15')
    # Check printer status before printing
    # if get_printer_status(printer_name):
    #     print(f"Printer {printer_name} is online")
    #     job_id = print_file("cv.pdf", printer_name, page="1")
    #     print("got job: ", job_id)

    #     get_printer_queue(printer_name)
    # else:
    #     print(f"Printer {printer_name} is offline or not found")