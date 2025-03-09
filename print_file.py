import os
import subprocess

def print_file(file_path, printer_name=None, page=None):
    """
    Print a file using lp command
    Args:
        file_path: Path to the file to print
        printer_name: Name of the printer (optional)
        page: Page number to print (optional)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    command = ['lp']
    
    if printer_name:
        command.extend(['-d', printer_name])
    
    if page:
        command.extend(['-p', str(page)])
    
    command.append(file_path)
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        # request id is Canon_LBP3010_LBP3018_LBP3050-1 (1 file(s))
        job_id = result.stdout.strip().split(' is ')[1].split(' (')[0]
        
        print(f"Print result: {result.stdout}")
        print(f"Successfully sent {file_path} to printer")
        print(f"Job ID: {job_id}")

        return job_id 
    except subprocess.CalledProcessError as e:
        print(f"Error printing file: {e}")
        return None

def get_printer_queue(printer_name=None):
    """
    Check printer queue using lpstat command
    Args:
        printer_name: Name of the printer (optional)
    """
    command = ['lpstat', '-W', 'all', '-o']
    
    if printer_name:
        command.extend(['-d', printer_name])
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("Printer Queue:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error checking printer queue: {e}")

def get_printer_state(printer_name=None):
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
        # printer Canon_LBP3010_LBP3018_LBP3050 is idle.  enabled since Sun Mar  9 12:50:20 2025

        if printer_name:
            print("Priter status : ", result.stdout) 
            printer_state = result.stdout.strip().split('.').split('is')[1].strip()
            print(f"print state is '{printer_state}'")

            return printer_state
         
    except subprocess.CalledProcessError as e:
        print(f"Error checking printer status: {e}")
        return None

def remove_print_job(job_id=None, printer_name=None):
    """
    Remove print jobs from queue using cancel command
    Args:
        job_id: ID of the job to remove (optional, removes all jobs if None)
        printer_name: Name of the printer (optional)
    """
    command = ['cancel']
    if printer_name and not job_id:
        command.append(printer_name)
    elif job_id:
        command.append(str(job_id))
    
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print("Remove job result:", result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error removing print job: {e}")

# Update the main section to include status check
if __name__ == "__main__":
    printer_name = "Canon_LBP3010_LBP3018_LBP3050"
    
    # Ask user for file name and page
    file_name = input("Enter the file name to print: ")
    page = input("Enter page number(s) to print (leave empty for all pages): ")
    
    # Check printer status before printing
    printer_state = get_printer_state(printer_name)
    
    if printer_state and printer_state == "idle":
        print(f"Printer {printer_name} is online and ready")
        job_id = print_file(file_name, printer_name, page=page if page else None)
        print(f"Print job submitted with ID: {job_id}")
    else:
        print(f"Printer {printer_name} is not ready or offline")
    
    # print(get_printer_status(printer_name))

    # get_printer_queue(printer_name)

    # remove_print_job(printer_name=printer_name, job_id='15')

    # Check printer status before printing
    # if get_printer_status(printer_name):
    #     print(f"Printer {printer_name} is online")
    #     job_id = print_file("cv.pdf", printer_name, page="1")
    #     print("got job: ", job_id)

    #     get_printer_queue(printer_name)
    # else:
    #     print(f"Printer {printer_name} is offline or not found")