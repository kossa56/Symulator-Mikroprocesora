import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import os

class SimulatorGUI:
    """Symulator procesora z interfejsem graficznym."""
    
    # Mapowanie nazw rejestrów (dla 8-bitowych)
    REG_MAP = {
        'AX': ('AX', None), 'AH': ('AX', 'high'), 'AL': ('AX', 'low'),
        'BX': ('BX', None), 'BH': ('BX', 'high'), 'BL': ('BX', 'low'),
        'CX': ('CX', None), 'CH': ('CX', 'high'), 'CL': ('CX', 'low'),
        'DX': ('DX', None), 'DH': ('DX', 'high'), 'DL': ('DX', 'low'),
    }
    VALID_REGS = set(REG_MAP.keys())

    def __init__(self, root):
        self.root = root
        self.root.title("Symulator Mikroprocesora")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        # Stan symulatora
        self.regs = {'AX': 0, 'BX': 0, 'CX': 0, 'DX': 0}
        self.program = []          # lista linii kodu
        self.pc = -1               # indeks bieżącej instrukcji (-1 = brak)
        self.running = False
        self.last_error = None

        # Zmienne do podświetlania
        self.current_line_tag = "current"

        # Tworzenie interfejsu
        self.create_widgets()
        self.update_register_display()
        self.update_program_display()

    def create_widgets(self):
        """Tworzy wszystkie elementy GUI."""
        # Główny podział na ramki: lewa (program) i prawa (rejestry + sterowanie)
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Lewa ramka - edytor programu
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="Program (jedna instrukcja na linię):", font=('Arial', 10, 'bold')).pack(anchor=tk.W)

        # Pole tekstowe z numerami linii (użyjemy Text + osobny numery)
        text_frame = tk.Frame(left_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # Numery linii
        self.line_numbers = tk.Text(text_frame, width=4, padx=3, takefocus=0, border=0,
                                    background='lightgrey', state='disabled')
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)

        # Główne pole edycji programu
        self.program_text = scrolledtext.ScrolledText(text_frame, wrap=tk.NONE, font=('Courier', 10))
        self.program_text.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Synchronizacja numerów linii
        self.program_text.bind('<KeyRelease>', self.on_text_change)
        self.program_text.bind('<MouseWheel>', self.on_text_change)
        self.program_text.bind('<Button-1>', self.on_text_change)
        self.update_line_numbers()

        # Przyciski sterowania programem
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        tk.Button(btn_frame, text="Wczytaj z pliku", command=self.load_file).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Zapisz do pliku", command=self.save_file).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Reset rejestrów", command=self.reset_registers).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Pomoc", command=self.show_help).pack(side=tk.LEFT, padx=2)

        # Prawa ramka - rejestry i sterowanie wykonaniem
        right_frame = tk.Frame(main_frame, width=300, bg='#f0f0f0')
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5,0))
        right_frame.pack_propagate(False)

        tk.Label(right_frame, text="Rejestry:", font=('Arial', 12, 'bold'), bg='#f0f0f0').pack(pady=5)

        # Ramka na wyświetlanie rejestrów (w formie siatki)
        reg_display_frame = tk.Frame(right_frame, bg='#f0f0f0')
        reg_display_frame.pack(pady=5)

        self.reg_labels = {}
        regs_order = ['AX', 'BX', 'CX', 'DX']
        for i, reg in enumerate(regs_order):
            # Etykieta nazwy rejestru
            tk.Label(reg_display_frame, text=reg, font=('Courier', 10, 'bold'), bg='#f0f0f0').grid(row=i*2, column=0, sticky=tk.W, pady=(5,0))
            # Wartość 16-bitowa
            self.reg_labels[reg] = tk.Label(reg_display_frame, text="0 (0x0000)", font=('Courier', 10), bg='white', relief=tk.SUNKEN, width=20, anchor=tk.W)
            self.reg_labels[reg].grid(row=i*2, column=1, padx=5, pady=(5,0))
            # 8-bitowe składowe
            high_name = reg[0] + 'H'
            low_name = reg[0] + 'L'
            tk.Label(reg_display_frame, text=f"{high_name}:", font=('Courier', 8), bg='#f0f0f0').grid(row=i*2+1, column=0, sticky=tk.W, padx=(10,0))
            self.reg_labels[high_name] = tk.Label(reg_display_frame, text="0", font=('Courier', 8), bg='white', relief=tk.SUNKEN, width=5)
            self.reg_labels[high_name].grid(row=i*2+1, column=1, sticky=tk.W, padx=5)
            tk.Label(reg_display_frame, text=f"{low_name}:", font=('Courier', 8), bg='#f0f0f0').grid(row=i*2+1, column=1, sticky=tk.E, padx=(50,0))
            self.reg_labels[low_name] = tk.Label(reg_display_frame, text="0", font=('Courier', 8), bg='white', relief=tk.SUNKEN, width=5)
            self.reg_labels[low_name].grid(row=i*2+1, column=1, sticky=tk.E, padx=(0,5))

        # Przyciski wykonawcze
        exec_frame = tk.Frame(right_frame, bg='#f0f0f0')
        exec_frame.pack(pady=10)

        tk.Button(exec_frame, text="Uruchom wszystko", command=self.run_all, width=15).pack(pady=2)
        tk.Button(exec_frame, text="Krok", command=self.step, width=15).pack(pady=2)
        tk.Button(exec_frame, text="Reset wykonania", command=self.reset_execution, width=15).pack(pady=2)

        # Obszar informacji o błędach
        tk.Label(right_frame, text="Komunikaty:", font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(pady=(10,0))
        self.error_text = tk.Text(right_frame, height=5, width=35, state='disabled', wrap=tk.WORD, bg='#ffe0e0')
        self.error_text.pack(pady=5, padx=5, fill=tk.X)

        # Przykładowy program do wstawienia
        self.insert_example_program()

    def insert_example_program(self):
        """Wstawia przykładowy program do edytora."""
        example = """MOV AX, 10
MOV BX, 20
ADD AX, BX
SUB CX, AX
MOV CL, 5
ADD DL, CL
MOV AH, 2
SUB AL, 3"""
        self.program_text.insert('1.0', example)
        self.on_text_change()

    def on_text_change(self, event=None):
        """Aktualizuje numery linii po zmianie tekstu."""
        self.update_line_numbers()
        self.update_program_list()

    def update_line_numbers(self):
        """Aktualizuje wyświetlanie numerów linii."""
        self.line_numbers.config(state='normal')
        self.line_numbers.delete('1.0', tk.END)

        # Pobierz liczbę linii w polu edycji
        content = self.program_text.get('1.0', tk.END)
        lines = content.split('\n')
        line_count = len(lines)

        line_numbers_str = "\n".join(str(i+1) for i in range(line_count))
        self.line_numbers.insert('1.0', line_numbers_str)
        self.line_numbers.config(state='disabled')

    def update_program_list(self):
        """Aktualizuje wewnętrzną listę programu na podstawie tekstu."""
        content = self.program_text.get('1.0', tk.END)
        self.program = [line.rstrip() for line in content.split('\n') if line.strip() != '' or line == '']
        # Uwaga: puste linie zachowujemy, ale będą pomijane podczas wykonywania

    def update_register_display(self):
        """Odświeża wyświetlanie wartości rejestrów."""
        for reg, val in self.regs.items():
            # 16-bitowy
            self.reg_labels[reg].config(text=f"{val} (0x{val:04X})")
            # 8-bitowe
            high_val = (val >> 8) & 0xFF
            low_val = val & 0xFF
            self.reg_labels[reg[0]+'H'].config(text=str(high_val))
            self.reg_labels[reg[0]+'L'].config(text=str(low_val))

    def update_program_display(self):
        """Podświetla bieżącą linię w edytorze."""
        # Usuń stare podświetlenie
        self.program_text.tag_remove(self.current_line_tag, '1.0', tk.END)
        if self.pc >= 0 and self.pc < len(self.program):
            # Podświetlenie linii o indeksie pc (licząc od 1)
            line_start = f"{self.pc+1}.0"
            line_end = f"{self.pc+1}.end"
            self.program_text.tag_add(self.current_line_tag, line_start, line_end)
            self.program_text.tag_config(self.current_line_tag, background='yellow', foreground='black')

    def log_error(self, msg):
        """Wyświetla komunikat o błędzie w polu tekstowym."""
        self.error_text.config(state='normal')
        self.error_text.insert(tk.END, msg + "\n")
        self.error_text.see(tk.END)
        self.error_text.config(state='disabled')
        self.last_error = msg

    def clear_error(self):
        """Czyści pole komunikatów."""
        self.error_text.config(state='normal')
        self.error_text.delete('1.0', tk.END)
        self.error_text.config(state='disabled')
        self.last_error = None

    # Operacje na rejestrach
    def get_reg(self, name):
        base, part = self.REG_MAP[name.upper()]
        val = self.regs[base]
        if part is None:
            return val & 0xFFFF
        elif part == 'high':
            return (val >> 8) & 0xFF
        else:
            return val & 0xFF

    def set_reg(self, name, value):
        base, part = self.REG_MAP[name.upper()]
        if part is None:
            self.regs[base] = value & 0xFFFF
        else:
            current = self.regs[base]
            if part == 'high':
                new = (current & 0x00FF) | ((value & 0xFF) << 8)
            else:
                new = (current & 0xFF00) | (value & 0xFF)
            self.regs[base] = new & 0xFFFF
        self.update_register_display()

    def parse_operand(self, op):
        op = op.upper()
        if op in self.VALID_REGS:
            return ('reg', op)
        try:
            val = int(op)
            return ('imm', val)
        except ValueError:
            raise ValueError(f"Nieznany operand: {op}")

    def disassemble(self, line):
        line = line.replace(',', ' ').strip()
        if not line or line.startswith(';'):
            return None  # komentarz lub pusta
        parts = line.split()
        if len(parts) < 3:
            raise ValueError("Za mało argumentów")
        op = parts[0].upper()
        if op not in ('MOV', 'ADD', 'SUB'):
            raise ValueError(f"Nieznana instrukcja: {op}")
        dest = parts[1].upper()
        src = parts[2].upper()
        if dest not in self.VALID_REGS:
            raise ValueError(f"Nieprawidłowy rejestr docelowy: {dest}")
        return (op, dest, src)

    def execute(self, op, dest, src):
        src_type, src_val = self.parse_operand(src)
        if src_type == 'reg':
            src_val = self.get_reg(src_val)
        dest_val = self.get_reg(dest)
        if op == 'MOV':
            result = src_val
        elif op == 'ADD':
            result = dest_val + src_val
        elif op == 'SUB':
            result = dest_val - src_val
        else:
            raise ValueError(f"Nieznana operacja: {op}")
        base, part = self.REG_MAP[dest]
        if part is None:
            result &= 0xFFFF
        else:
            result &= 0xFF
        self.set_reg(dest, result)

    def step(self):
        """Wykonuje jedną instrukcję (jeśli możliwe)."""
        self.clear_error()
        if self.pc < 0 or self.pc >= len(self.program):
            self.log_error("Brak programu lub koniec programu.")
            self.running = False
            return False

        # Pomiń puste linie i komentarze
        while self.pc < len(self.program):
            line = self.program[self.pc].strip()
            if line and not line.startswith(';'):
                break
            self.pc += 1

        if self.pc >= len(self.program):
            self.log_error("Koniec programu.")
            self.running = False
            return False

        line = self.program[self.pc].strip()
        try:
            op, dest, src = self.disassemble(line)
            self.execute(op, dest, src)
            self.pc += 1
            self.update_program_display()
            return True
        except Exception as e:
            self.log_error(f"Błąd w linii {self.pc+1}: {e}")
            self.running = False
            self.update_program_display()
            return False

    def run_all(self):
        """Wykonuje program do końca."""
        self.clear_error()
        if not self.program:
            self.log_error("Program jest pusty.")
            return
        self.reset_execution()  # ustaw pc na 0
        self.running = True
        while self.running and self.pc < len(self.program):
            if not self.step():
                break
        if self.pc >= len(self.program):
            self.log_error("Program zakończony.")

    def reset_registers(self):
        """Zeruje wszystkie rejestry."""
        for r in self.regs:
            self.regs[r] = 0
        self.update_register_display()
        self.clear_error()

    def reset_execution(self):
        """Resetuje licznik rozkazów na początek programu."""
        self.pc = 0
        self.running = False
        self.update_program_display()
        self.clear_error()

    def load_file(self):
        """Wczytuje program z pliku."""
        fname = filedialog.askopenfilename(filetypes=[("Pliki tekstowe", "*.txt"), ("Wszystkie pliki", "*.*")])
        if not fname:
            return
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                content = f.read()
            self.program_text.delete('1.0', tk.END)
            self.program_text.insert('1.0', content)
            self.on_text_change()
            self.reset_execution()
            self.clear_error()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie można wczytać pliku:\n{e}")

    def save_file(self):
        """Zapisuje program do pliku."""
        fname = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Pliki tekstowe", "*.txt"), ("Wszystkie pliki", "*.*")])
        if not fname:
            return
        try:
            content = self.program_text.get('1.0', tk.END)
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Info", "Program zapisany.")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie można zapisać pliku:\n{e}")

    def show_help(self):
        """Wyświetla okno pomocy."""
        help_text = """
INSTRUKCJA OBSŁUGI (dla totalnego idioty):

1. Wpisz program w lewym oknie. Każda instrukcja w osobnej linii.
   Dozwolone rozkazy: MOV, ADD, SUB.
   Argumenty: rejestry (AX, AH, AL, BX, BH, BL, CX, CH, CL, DX, DH, DL) lub liczby dziesiętne.
   Przykład: MOV AX, 5
             ADD BX, AX
             SUB CL, 3

2. Kliknij "Uruchom wszystko" aby wykonać program od początku do końca.
   Klikaj "Krok" aby wykonywać program pojedynczo.
   "Reset wykonania" ustawia wskaźnik na pierwszą linię.

3. Rejestry są wyświetlane po prawej: wartości 16-bitowe i 8-bitowe (H - starszy bajt, L - młodszy).

4. Bieżąca linia jest podświetlona na żółto.

5. Możesz zapisać program do pliku i wczytać go ponownie.

6. W razie błędu zobaczysz komunikat na dole po prawej.

"""
        messagebox.showinfo("Pomoc", help_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = SimulatorGUI(root)
    root.mainloop()