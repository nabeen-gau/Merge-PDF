from tkinter import filedialog, messagebox, Entry, Frame, Label, Canvas, PhotoImage, Tk, Menu, Button
from tkinter.ttk import Scrollbar
from os import startfile
from os.path import basename
from PyPDF2 import PdfMerger
from PdfViewer import ShowPdf


class SpFrame(Frame):
    pos = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class TiledView(Canvas):
    list_of_elements = {}
    _selected = None
    snap_height = 55
    offset_pos = 0
    elem_height = 50
    elem_spacing = 5
    pady = 5
    padx = (5, 5)
    background = 'white'

    def __init__(self, *args, **kwargs):
        self.set_properties(kwargs)
        # create a main frame
        self.main_frame = Frame(*args, **kwargs)
        self.main_frame.pack(expand=True, fill='both')

        # create a canvas
        self.canvas = Canvas(self.main_frame)
        self.canvas.pack(anchor='nw', side='left', fill='both', expand=True)

        # add a scrollbar to the canvas
        self.scr_vert = Scrollbar(self.main_frame, orient='vertical', command=self.canvas.yview)
        self.scr_vert.pack(anchor='e', side='right', fill='y')

        # create another frame inside the canvas
        self.frame = Frame(self.canvas)
        super().__init__(self.frame, **kwargs)

        self.bind_all('<Button-1>', lambda e: self.btn_clicked())
        self.bind_all('<ButtonRelease-1>', lambda e: self.drag_stopped())

    def set_properties(self, kwargs):
        self.background = kwargs['background']

    def set_scroll_region(self, region=(0, 0, 0, 0)):
        # configure the canvas
        self.canvas.configure(yscrollcommand=self.scr_vert.set)
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=region))

        # add that new frame to a window in the canvas
        self.canvas.create_window((0, 0), window=self.frame, anchor='nw')

        # binding mousewheel to scroll
        self.canvas.bind('<Enter>', lambda e: self._bound_to_mousewheel())
        self.canvas.bind('<Leave>', lambda e: self._unbound_to_mousewheel())

    # function that runs on entering the fame widget
    def _bound_to_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    # function that runs on leaving the frame widget
    def _unbound_to_mousewheel(self):
        self.canvas.unbind_all("<MouseWheel>")

    # function that runs on scrolling the mousewheel
    def _on_mousewheel(self, event):
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def set_elem_prop(self,
                      height=50,
                      spacing=5,
                      pady=5,
                      padx=(5, 5)
                      ):
        self.elem_height = height
        self.elem_spacing = spacing
        self.pady = pady
        self.padx = padx
        self.snap_height = height + spacing
        self.pack_propagate(False)

    def add_elements(self, n=1, bg='white'):
        y = 0
        for num in range(n):
            f = SpFrame(self, height=self.elem_height, background=bg)
            self.list_of_elements[f] = len(self.list_of_elements)
            x = self.padx[0]
            if len(self.list_of_elements) == 1:
                y = self.pady
            else:
                y = self.pady + (self.elem_height + self.elem_spacing) * (len(self.list_of_elements) - 1)
            rw = 1 - self.padx[1] / float(self.winfo_reqwidth())
            self.bind('<Configure>', lambda e: self.configure_handler(e, self.padx))
            f.place(x=x, y=y, relwidth=rw)

            f.bind('<Enter>', lambda e, elem=f: self.highlight_elem_color(elem))
        self.set_scroll_region((0, 0, 0, y))
        self.configure(height=y if y > self.winfo_screenheight() else self.winfo_screenheight(),
                       width=self.winfo_screenwidth())

    def remove_element(self, elem):
        index = self.list_of_elements[elem]
        elem.destroy()
        self.list_of_elements.pop(elem)
        for i in self.list_of_elements.keys():
            if self.list_of_elements[i] > index:
                self.list_of_elements[i] -= 1
        self.snap_positions()

    def highlight_elem_color(self, elem):
        for obj in elem.winfo_children():
            obj.configure(background='#e5f3ff')
        elem.configure(background='#e5f3ff')
        elem.bind('<Leave>', lambda e: self.rem_highlight_elem_color(elem))

    @staticmethod
    def rem_highlight_elem_color(elem):
        for obj in elem.winfo_children():
            obj.configure(background='#ffffff')
        elem.configure(background='#ffffff')
        elem.unbind('<Leave>')

    def configure_handler(self, event, x):
        rw = 1 - (x[0] + x[1]) / event.width
        for tile in self.list_of_elements:
            tile.place_configure(relwidth=rw)

    # Method that returns the widget under the mouse
    def get_selected_widget(self):
        x, y = self.winfo_pointerxy()
        widget = self.winfo_containing(x, y)
        return widget

    def btn_clicked(self):
        self._selected = self.get_selected_widget()

        if isinstance(self._selected, Scrollbar) or self._selected is None or isinstance(self._selected, Tk):
            return

        while self._selected not in self.winfo_children():
            self._selected = self._selected.master
            if self._selected is None:
                return
        self._selected.configure(background='#cce8ff')
        for i in self._selected.winfo_children():
            if i is None:
                break
            i.configure(background='#cce8ff')
        self._selected.tkraise()
        self._selected.pos = self.winfo_pointery()

        self.offset_pos = self.winfo_pointery() - self._selected.winfo_rooty() - self.pady

        self.bind_all('<B1-Motion>', lambda ev: self.mouse_drag_event())

    def mouse_drag_event(self):
        if self._selected.pos != self.winfo_pointery():
            self._selected.place_configure(y=self.winfo_pointery() - self.winfo_rooty() - self.offset_pos)

        self._selected.pos = self.winfo_pointery()

    def drag_stopped(self):
        if isinstance(self._selected, Scrollbar) or self._selected is None or isinstance(self._selected, Tk):
            return
        self.unbind_all('<B1-Motion>')
        self.calc_new_position()
        self.snap_positions()

    def calc_new_position(self):
        if int(self._selected.place_info()['y']) < 0:
            self._selected.place_configure(y=self.pady)

        current_pos = int(self._selected.place_info()['y'])
        r = (current_pos - self.pady) / self.snap_height
        if abs(int(r) - r) > 0.5:
            snap_row = int(r) + 1
        else:
            snap_row = int(r)
        if snap_row >= len(self.list_of_elements):
            snap_row = len(self.list_of_elements) - 1
        for tile in self.list_of_elements:
            sel = self.list_of_elements[self._selected]
            cur = self.list_of_elements[tile]
            if tile == self._selected or cur < sel and cur < snap_row:
                continue
            elif snap_row > cur > sel or cur == snap_row > sel:
                self.list_of_elements[tile] -= 1
            elif snap_row < cur < sel or cur == snap_row < sel:
                self.list_of_elements[tile] += 1
            else:
                continue

        self.list_of_elements[self._selected] = snap_row

    def snap_positions(self):
        for tile in self.list_of_elements:
            tile.place_configure(y=self.list_of_elements[tile] * (self.elem_spacing + self.elem_height) + self.pady)


class App:
    # initializing variables
    font = ('device', 10)
    count = 0
    file = ShowPdf()
    file.set_dpi(100)

    _selected = None
    frame = None
    pdf_view = None
    frame_left = None

    pdf_files = []
    pdf_filenames = []

    def __init__(self):
        # Creating tkinter window
        self.window = Tk()
        self.w_width = int(self.window.winfo_vrootwidth() / 2)
        self.w_height = int(self.window.winfo_vrootheight() / 1.5)
        # self.window.wm_maxsize(self.window.winfo_screenwidth(), self.window.winfo_screenheight())
        # self.window.wm_resizable(False, False)
        self.set_default_window_size()
        self.window.title('PdfTools')
        self.window.iconbitmap(r"D:\Pycharm\pdf_icon.ico")
        self.window.protocol("WM_DELETE_WINDOW", self._quit)

        # Icon definition for pdf files
        self.img = PhotoImage(file=r'D:\Pycharm\pdf_icon.png')

        # Setting up menu bar
        self.menu = Menu(self.window)

        self.file_items = Menu(self.menu, tearoff=0, font=self.font)
        self.file_items.add_command(label='Add files', command=self.select_files)
        self.file_items.add_command(label='Exit', command=self._quit)

        self.command_items = Menu(self.menu, tearoff=0)
        self.command_items.add_command(label='Merge PDF', command=self.merge_pdf)
        self.command_items.add_command(label='Clear all selection', command=self.clear_frame)

        setting_items = Menu(self.menu, tearoff=0)
        setting_items.add_command(label='Change DPI for PDF view', command=self.change_dpi_for_pdf_viewer)

        self.menu.add_cascade(label='File', menu=self.file_items)
        self.menu.add_cascade(label='Command', menu=self.command_items)
        self.menu.add_cascade(label='Settings', menu=setting_items)
        self.window.config(menu=self.menu)

        self.frame_left = Frame(self.window)
        self.frame_left.pack(fill='both', side='left', expand=True)

        # Adding scrolling frame in window
        self.frame = TiledView(self.frame_left, background='#ffffff')
        self.frame.set_elem_prop(height=24, pady=0, padx=(0, 0), spacing=0)
        self.frame.pack(fill='both', expand=True)

        # Initializing tabs for open pdf
        self.open_pdf_tabs = Frame(self.window)

        # Defining right click menu
        self.right_click_menu = Menu(self.window, tearoff=0)
        self.right_click_menu.add_command(label='Open', command=self.open_pdf)
        self.right_click_menu.add_command(label='Remove', command=self.remove_pdf_file)

        self.window.bind('<Button-3>', self.right_click_menu_popup)
        # Running the GUI
        self.window.mainloop()

    # change dpi for pdf view
    def change_dpi_for_pdf_viewer(self):
        temp_window = Tk()
        h = self.window.winfo_vrootheight()
        w = self.window.winfo_vrootwidth()
        temp_window.geometry(f'200x100+{int(w / 4)}+{int(h / 6)}')
        temp_window.title('Change DPI')
        Label(temp_window, text='DPI Value').pack()
        e = Entry(temp_window)
        e.pack()

        def set_dpi():
            if e.get() == '':
                return
            try:
                val = int(e.get())
            except ValueError:
                messagebox.showinfo('Error!!!', 'Only accepts integer value')
                temp_window.destroy()
                return
            self.file.set_dpi(val)

            temp_window.destroy()

        Button(temp_window, text='Enter', command=set_dpi).pack()
        temp_window.mainloop()

    # for opening pdf in new tab
    def open_pdf(self):
        self.open_pdf_tabs.pack(expand=True, fill='both', side='right')
        self.create_new_tab()

    # for creating new tab for displaying pdf
    def create_new_tab(self):
        while self._selected not in self.frame.list_of_elements:
            self._selected = self._selected.master
            if self._selected is None:
                return
        index = list(self.frame.list_of_elements.keys()).index(self._selected)
        path = self.pdf_files[index]
        self.show_pdf(self.open_pdf_tabs, path)

    # for displaying pdf files
    def show_pdf(self, master, path):
        if self.pdf_view is not None:
            self.pdf_view.destroy()
        self.pdf_view = self.file.pdf_view(master, pdf_location=path)
        self.pdf_view.pack(fill='both', expand=True)

    # for maximizing the window
    def maximize(self):
        self.window.state('zoomed')

    # removes pdf file
    def remove_pdf_file(self):
        while self._selected not in self.frame.list_of_elements:
            self._selected = self._selected.master
            if self._selected is None:
                return
        index = list(self.frame.list_of_elements.keys()).index(self._selected)
        self.pdf_filenames.pop(index)
        self.pdf_files.pop(index)
        self.count -= 1
        self.frame.remove_element(self._selected)

    # defining right click menu popup
    def right_click_menu_popup(self, event):
        self._selected = self.frame.get_selected_widget()
        try:
            self.right_click_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.right_click_menu.grab_release()

    # for quiting the program
    def _quit(self):
        self.window.quit()
        self.window.destroy()

    # for minimizing the window or setting the window to default pos and size
    def set_default_window_size(self):
        h = self.window.winfo_vrootheight()
        w = self.window.winfo_vrootwidth()
        self.window.geometry(f'{int(w / 2)}x{int(h / 1.5)}+{int(w / 4)}+{int(h / 6)}')

    # for selecting pdf files
    def select_files(self):
        self.pdf_files += [*filedialog.askopenfilenames(title='Choose pdf files',
                                                        filetypes=(('pdf files', '*.pdf'), ('all files', '*.*')))]
        self.pdf_filenames = [basename(i) for i in self.pdf_files]
        if not self.pdf_files:
            return
        else:
            self.display_sel_files()
            x, y = self.get_window_size()
            self.window.state('normal')  # normal, iconic, withdrawn, zoomed
            # Updating windows to enable scroll for weird reasons
            self.window.geometry(f'{x + 1}x{y + 1}')
            self.window.geometry(f'{x - 1}x{y - 1}')

    # returns current window size
    def get_window_size(self):
        return self.window.winfo_width(), self.window.winfo_height()

    # for merging selected pdf files
    def merge_pdf(self):
        # check if updating list is necessary
        # not sure why checking is necessary^^^^
        if True:
            self.update_after_moving()

        if len(self.pdf_files) < 2:
            messagebox.showinfo('Error!!!', 'Add at least 2 files')
            return
        pdfs = self.pdf_files
        merger = PdfMerger()
        for pdf in pdfs:
            merger.append(pdf)
        file = filedialog.asksaveasfilename(title='Choose save location',
                                            defaultextension='*.pdf',
                                            filetypes=(('PDF file', '*.pdf'), ('All files', '*.*')))
        if file == '':
            merger.close()
            return
        merger.write(file)
        merger.close()
        startfile(file)

    # for updating the pdf item list after dragging them
    def update_after_moving(self):
        new_list = []
        for i in range(len(self.pdf_files)):
            new_list.append(self.pdf_files[list(self.frame.list_of_elements.values()).index(i)])

        self.pdf_files = new_list

    # for clearing frame objects
    def clear_frame(self):
        for i in self.frame.list_of_elements.keys():
            i.destroy()
        self.pdf_filenames = []
        self.pdf_files = []
        self.count = 0
        self.frame.list_of_elements = {}

    # for displaying selected pdf files on screen
    def display_sel_files(self):
        length = len(self.pdf_filenames)
        self.frame.add_elements(n=length - self.count, bg='#ffffff')

        for i in list(self.frame.list_of_elements.keys())[self.count:length]:
            i.pack_propagate(False)
            Label(i, image=self.img).pack(padx=5, side='left')
            Label(i, text=self.pdf_filenames[list(self.frame.list_of_elements.keys()).index(i)],
                  background='#ffffff', foreground='black').pack(padx=5, anchor='w', side='left')
        self.count = length


if __name__ == '__main__':
    App()
