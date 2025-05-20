import os
import sys
import subprocess
import time
import signal
from sqlmap_ai.ui import print_info, print_warning, print_error, print_success
class SQLMapRunner:
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sqlmap_path = os.path.join(self.script_dir, "sqlmap")
        self.sqlmap_script = os.path.join(self.sqlmap_path, "sqlmap.py")
        if not os.path.exists(self.sqlmap_script):
            print_error(f"sqlmap.py not found in {self.sqlmap_path}. Make sure sqlmap is in the correct directory.")
            sys.exit(1)
    def run_sqlmap(self, target_url, options, timeout=180, interactive_mode=False):
        command = [sys.executable, self.sqlmap_script, "--url", target_url]
        if isinstance(options, str):
            options = options.split()
        filtered_options = []
        has_batch_flag = False
        has_threads_flag = False
        for opt in options:
            if opt == "--batch":
                if not has_batch_flag:
                    filtered_options.append(opt)
                    has_batch_flag = True
            elif opt.startswith("--threads="):
                has_threads_flag = True
                filtered_options.append(opt)
            else:
                filtered_options.append(opt)
        command.extend(filtered_options)
        command.extend(["-v", "1"])  
        if not has_threads_flag:
            command.append("--threads=5")
        if not interactive_mode and not has_batch_flag:
            command.append("--batch")
        command_str = ' '.join(command)
        print_info(f"Executing SQLMap command: {command_str}")
        print_info(f"Timeout set to {timeout} seconds. Press Ctrl+C to cancel.")
        try:
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  
            )
            output_lines = []
            start_time = time.time()
            last_output_time = start_time
            progress_indicators = ['[INFO]', '[WARNING]', '[*]', '[+]', '[!]']
            stall_timeout = min(timeout * 0.3, 60)  
            poll_interval = 0.1
            timed_out = False
            stalled = False
            last_progress_message = ""
            last_progress_time = time.time()
            same_progress_count = 0
            spinner_chars = ['|', '/', '-', '\\']
            spinner_idx = 0
            last_spinner_update = time.time()
            spinner_interval = 0.2  
            print_info("Starting SQLMap scan...")
            print_info("Running", end='', flush=True)
            while True:
                return_code = process.poll()
                if return_code is not None:
                    break
                current_time = time.time()
                if current_time - last_spinner_update >= spinner_interval:
                    print(f"\b{spinner_chars[spinner_idx]}", end='', flush=True)
                    spinner_idx = (spinner_idx + 1) % len(spinner_chars)
                    last_spinner_update = current_time
                elapsed_time = time.time() - start_time
                time_since_last_output = time.time() - last_output_time
                if elapsed_time > timeout:
                    print("\b \nSQLMap command timeout after {:.1f} seconds".format(elapsed_time))
                    print_warning(f"SQLMap command timeout after {elapsed_time:.1f} seconds")
                    timed_out = True
                    break
                if time_since_last_output > stall_timeout:
                    print("\b \nNo output for {:.1f} seconds. Process may be stalled.".format(time_since_last_output))
                    print_warning(f"No output for {time_since_last_output:.1f} seconds. Process may be stalled.")
                    stalled = True
                    break
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    last_output_time = time.time()
                    if any(indicator in line for indicator in progress_indicators):
                        print("\b \b", end='', flush=True)
                        status_line = line.strip()
                        for indicator in progress_indicators:
                            if indicator in status_line:
                                status_message = status_line.split(indicator, 1)[1].strip()
                                if status_message and len(status_message) > 5:  
                                    if len(status_message) > 60:
                                        status_message = status_message[:57] + "..."
                                    print(f"\r\033[K{indicator} {status_message}")
                                    print("Running", end='', flush=True)
                                break
                        for indicator in progress_indicators:
                            if indicator in line:
                                progress_message = line.split(indicator, 1)[1].strip()
                                if progress_message:
                                    if progress_message == last_progress_message:
                                        same_progress_count += 1
                                        if same_progress_count > 10 and (time.time() - last_progress_time > stall_timeout):
                                            print("\b \nSQLMap appears to be stuck in a loop.")
                                            print_warning("SQLMap appears to be stuck in a loop.")
                                            stalled = True
                                            break
                                    else:
                                        same_progress_count = 0
                                        last_progress_message = progress_message
                                        last_progress_time = time.time()
                    if interactive_mode:
                        print(line, end='')
                    output_lines.append(line)
                if stalled:
                    break
                time.sleep(poll_interval)
            print("\b \b", end='', flush=True)
            print() 
            if timed_out or stalled:
                try:
                    print_warning(f"Terminating SQLMap process due to {'timeout' if timed_out else 'stalled process'}")
                    self._kill_sqlmap_process(process)
                except Exception as e:
                    print_error(f"Failed to terminate process: {str(e)}")
            for line in process.stdout:
                if interactive_mode:
                    print(line, end='')
                output_lines.append(line)
            process.stdout.close()
            full_output = ''.join(output_lines)
            if timed_out:
                from sqlmap_ai.parser import extract_sqlmap_info
                partial_info = extract_sqlmap_info(full_output)
                if any(partial_info.values()):
                    print_warning("Scan timed out, but some useful information was collected.")
                    full_output = "TIMEOUT_WITH_PARTIAL_DATA: " + full_output
                else:
                    full_output = "TIMEOUT: Command execution exceeded time limit"
            elif stalled:
                print_warning("SQLMap appeared to be stalled or in a loop.")
                full_output = "STALLED: " + full_output
            elif return_code != 0:
                print_warning(f"SQLMap command completed with non-zero return code {return_code}")
                if "Connection refused" in full_output:
                    print_error("Connection refused - Target may not be reachable")
                    return "ERROR: Connection refused - Target may not be reachable"
                elif "unable to connect to the target URL" in full_output:
                    print_error("Unable to connect to the target URL")
                    return "ERROR: Unable to connect to the target URL"
                elif "problem occurred while parsing an URL" in full_output:
                    print_error("Problem parsing URL - Make sure URL format is correct")
                    return "ERROR: Problem parsing URL - Make sure URL format is correct"
                elif "No parameter(s) found for testing" in full_output:
                    print_warning("No parameters found for testing in the URL")
                    return "WARNING: No parameter(s) found for testing in the URL"
                else:
                    print_warning("Command failed but analysis will proceed with available output")
            if not (timed_out or stalled):
                print_success("SQLMap execution completed" + (" with warnings" if return_code != 0 else ""))
            if not interactive_mode:
                print("\n".join(output_lines[-20:]))  
                print_info("Showing last 20 lines of output. Full results will be analyzed.")
            return full_output
        except KeyboardInterrupt:
            print("\b \b", end='', flush=True)  
            print("\nProcess interrupted by user")
            print_warning("\nProcess interrupted by user")
            try:
                process.terminate()
                time.sleep(0.5)
                if process.poll() is None:
                    process.kill()
            except:
                pass
            return "INTERRUPTED: Process was stopped by user"
        except Exception as e:
            print("\b \b", end='', flush=True)  
            print_error(f"Failed to execute SQLMap: {str(e)}")
            return None
    def _kill_sqlmap_process(self, process):
        try:
            process.terminate()
            time.sleep(0.5)
            if process.poll() is None:
                print_warning("Process did not terminate gracefully, forcing kill")
                if sys.platform.startswith('win'):
                    try:
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], 
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                    except:
                        process.kill()
                else:
                    try:
                        pgid = os.getpgid(process.pid)
                        os.killpg(pgid, signal.SIGKILL)
                    except:
                        process.kill()
                time.sleep(1)
                if process.poll() is None:
                    print_error("Failed to kill process - might need manual termination")
        except Exception as e:
            print_error(f"Error killing SQLMap process: {str(e)}")
    def gather_info(self, target_url, timeout=120, interactive=False):
        print_info("Running basic fingerprinting and database enumeration...")
        print_info("This will identify the database type and list available databases.")
        print_info("If scan takes too long, you can press Ctrl+C to interrupt it")
        try:
            result = self.run_sqlmap(
                target_url, 
                ["--fingerprint", "--dbs", "--threads=5"], 
                timeout=timeout, 
                interactive_mode=interactive
            )
            return result
        except Exception as e:
            print_error(f"Error running basic scan: {str(e)}")
            return None
    def fallback_options_for_timeout(self, target_url):
        print_info("Original scan timed out. Running with more focused options...")
        print_info("This will attempt a faster scan with fewer test vectors.")
        fallback_options = [
            "--technique=BT",   
            "--level=1",        
            "--risk=1",         
            "--time-sec=1",     
            "--timeout=10",     
            "--retries=1",      
            "--threads=8",      
            "--dbs"             
        ]
        try:
            result = self.run_sqlmap(
                target_url, 
                fallback_options,
                timeout=90
            )
            return result
        except Exception as e:
            print_error(f"Error running fallback scan: {str(e)}")
            return None 