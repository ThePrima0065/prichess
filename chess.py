import pygame
import sys
import os

def get_piece_value(piece):
    if not piece:
        return 0
    ptype = piece[1]
    values = {'p': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0}
    return values.get(ptype, 0)

class GameState:
    def __init__(self, board, current_player, king_positions, has_moved, en_passant_target, en_passant_pawn, halfmove_clock=0, last_sound_type=None, last_move=None, white_time=60, black_time=60, first_move_made=False, white_made_first=False, black_made_first=False, white_captured_value=0, black_captured_value=0, flipped=False):
        self.board = [row[:] for row in board]
        self.current_player = current_player
        self.king_positions = king_positions.copy()
        self.has_moved = has_moved.copy()
        self.en_passant_target = en_passant_target
        self.en_passant_pawn = en_passant_pawn
        self.halfmove_clock = halfmove_clock
        self.last_sound_type = last_sound_type
        self.last_move = last_move
        self.white_time = white_time
        self.black_time = black_time
        self.first_move_made = first_move_made
        self.white_made_first = white_made_first
        self.black_made_first = black_made_first
        self.white_captured_value = white_captured_value
        self.black_captured_value = black_captured_value
        self.flipped = flipped

class ChessGame:
    def __init__(self, base_time=60, increment=0):
        self.board = self.create_board()
        self.current_player = 'w'
        self.king_positions = {'w': (7, 4), 'b': (0, 4)}
        self.has_moved = {
            'wK': False, 'wR_a': False, 'wR_h': False,
            'bK': False, 'bR_a': False, 'bR_h': False
        }
        self.en_passant_target = None
        self.en_passant_pawn = None
        self.selected = None
        self.valid_moves = []
        self.history = []
        self.promotion_pending = None
        self.position_history = []
        self.halfmove_clock = 0
        self.last_move = None
        self.game_over = False
        self.winner = None
        self.draw_offered = False
        self.resigned = False
        self.base_time = base_time
        self.increment = increment
        self.white_time = float(base_time)
        self.black_time = float(base_time)
        self.first_move_made = False
        self.white_made_first = False
        self.black_made_first = False
        self.white_captured_value = 0
        self.black_captured_value = 0
        self.last_tick = None
        self.flipped = False  # ← Needed for coordinate drawing
        self.add_current_position_to_history()

    def create_board(self):
        return [
            ['bR', 'bN', 'bB', 'bQ', 'bK', 'bB', 'bN', 'bR'],
            ['bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp'],
            [None]*8,
            [None]*8,
            [None]*8,
            [None]*8,
            ['wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp'],
            ['wR', 'wN', 'wB', 'wQ', 'wK', 'wB', 'wN', 'wR']
        ]

    # ... [rest of ChessGame methods unchanged: get_position_key, is_path_clear, is_valid_move, etc.] ...
    # (All methods below are identical to your working version — only `flip` and drawing will use `flipped`)

    def get_position_key(self):
        board_str = ''.join(
            piece if piece else '.'
            for row in self.board
            for piece in row
        )
        castling = ''.join([
            'K' if not self.has_moved.get('wK', True) else '',
            'Q' if not self.has_moved.get('wR_a', True) else '',
            'k' if not self.has_moved.get('bK', True) else '',
            'q' if not self.has_moved.get('bR_a', True) else ''
        ]) or '-'
        ep = str(self.en_passant_target) if self.en_passant_target else '-'
        return (board_str, self.current_player, castling, ep)

    def add_current_position_to_history(self):
        self.position_history.append(self.get_position_key())

    def is_path_clear(self, start, end):
        sr, sc = start
        er, ec = end
        dr = 0 if er == sr else (1 if er > sr else -1)
        dc = 0 if ec == sc else (1 if ec > sc else -1)
        r, c = sr + dr, sc + dc
        while (r, c) != (er, ec):
            if self.board[r][c] is not None:
                return False
            r += dr
            c += dc
        return True

    def is_valid_move(self, start, end):
        if self.promotion_pending:
            return False
        sr, sc = start
        er, ec = end
        piece = self.board[sr][sc]
        if piece is None or piece[0] != self.current_player:
            return False
        target = self.board[er][ec]
        if target and target[0] == self.current_player:
            return False
        ptype = piece[1]
        row_diff = er - sr
        col_diff = ec - sc
        if ptype == 'p':
            direction = -1 if self.current_player == 'w' else 1
            start_row = 6 if self.current_player == 'w' else 1
            if sc == ec:
                if er == sr + direction and target is None:
                    return True
                if sr == start_row and er == sr + 2*direction and target is None and self.board[sr + direction][sc] is None:
                    return True
            elif abs(col_diff) == 1 and er == sr + direction and target:
                return True
            elif abs(col_diff) == 1 and er == sr + direction and target is None and self.en_passant_target == (er, ec):
                return True
            return False
        elif ptype == 'R':
            return (sr == er or sc == ec) and self.is_path_clear(start, end)
        elif ptype == 'N':
            return (abs(row_diff) == 2 and abs(col_diff) == 1) or (abs(row_diff) == 1 and abs(col_diff) == 2)
        elif ptype == 'B':
            return abs(row_diff) == abs(col_diff) and self.is_path_clear(start, end)
        elif ptype == 'Q':
            return ((sr == er or sc == ec or abs(row_diff) == abs(col_diff))) and self.is_path_clear(start, end)
        elif ptype == 'K':
            if abs(col_diff) == 2 and sr == er:
                if self.has_moved.get(f'{self.current_player}K', False):
                    return False
                rook_col = 0 if col_diff < 0 else 7
                rook_key = f'{self.current_player}R_{"a" if rook_col == 0 else "h"}'
                if self.has_moved.get(rook_key, False):
                    return False
                if col_diff < 0:
                    path_clear = all(self.board[sr][c] is None for c in range(sc-1, sc-4, -1))
                else:
                    path_clear = all(self.board[sr][c] is None for c in range(sc+1, sc+3))
                if not path_clear:
                    return False
                if col_diff < 0:
                    middle_sq = (sr, sc - 1)
                else:
                    middle_sq = (sr, sc + 1)
                temp_king_pos = self.king_positions[self.current_player]
                self.king_positions[self.current_player] = middle_sq
                in_check_middle = self.is_in_check(self.current_player)
                self.king_positions[self.current_player] = temp_king_pos
                if in_check_middle:
                    return False
                return True
            return abs(row_diff) <= 1 and abs(col_diff) <= 1
        return False

    def is_in_check(self, player):
        king_pos = self.king_positions[player]
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece[0] != player:
                    if self.is_valid_attack((r, c), king_pos):
                        return True
        return False

    def is_valid_attack(self, start, end):
        sr, sc = start
        er, ec = end
        piece = self.board[sr][sc]
        if not piece:
            return False
        ptype = piece[1]
        row_diff = er - sr
        col_diff = ec - sc
        if ptype == 'p':
            direction = -1 if piece[0] == 'w' else 1
            return er == sr + direction and abs(col_diff) == 1
        if ptype == 'R':
            return (sr == er or sc == ec) and self.is_path_clear(start, end)
        if ptype == 'B':
            return abs(row_diff) == abs(col_diff) and self.is_path_clear(start, end)
        if ptype == 'Q':
            return ((sr == er or sc == ec or abs(row_diff) == abs(col_diff))) and self.is_path_clear(start, end)
        if ptype == 'K':
            return abs(row_diff) <= 1 and abs(col_diff) <= 1
        if ptype == 'N':
            return (abs(row_diff) == 2 and abs(col_diff) == 1) or (abs(row_diff) == 1 and abs(col_diff) == 2)
        return False

    def is_checkmate(self, player):
        if not self.is_in_check(player):
            return False
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece[0] == player:
                    if self.get_valid_moves((r, c)):
                        return False
        return True

    def is_stalemate(self, player):
        if self.is_in_check(player):
            return False
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece[0] == player:
                    if self.get_valid_moves((r, c)):
                        return False
        return True

    def is_insufficient_material(self):
        white_pieces = []
        black_pieces = []
        for row in self.board:
            for piece in row:
                if piece:
                    if piece[0] == 'w':
                        white_pieces.append(piece[1])
                    else:
                        black_pieces.append(piece[1])

        def is_minor_only(pieces):
            filtered = [p for p in pieces if p != 'K']
            if not filtered:
                return True
            for p in filtered:
                if p not in ('B', 'N'):
                    return False
            return True

        if not is_minor_only(white_pieces) or not is_minor_only(black_pieces):
            return False

        white_minors = [p for p in white_pieces if p != 'K']
        black_minors = [p for p in black_pieces if p != 'K']

        if not white_minors and not black_minors:
            return True
        if (len(white_minors) == 1 and not black_minors) or (not white_minors and len(black_minors) == 1):
            return True
        if len(white_minors) == 1 and len(black_minors) == 1:
            if white_minors[0] == 'B' and black_minors[0] == 'B':
                white_bishop_sq = None
                black_bishop_sq = None
                for r in range(8):
                    for c in range(8):
                        piece = self.board[r][c]
                        if piece == 'wB':
                            white_bishop_sq = (r, c)
                        elif piece == 'bB':
                            black_bishop_sq = (r, c)
                if white_bishop_sq and black_bishop_sq:
                    w_color = (white_bishop_sq[0] + white_bishop_sq[1]) % 2
                    b_color = (black_bishop_sq[0] + black_bishop_sq[1]) % 2
                    if w_color == b_color:
                        return True
        all_pieces = white_pieces + black_pieces
        for p in all_pieces:
            if p in ('p', 'R', 'Q'):
                return False
        return True

    def is_threefold_repetition(self):
        current_key = self.get_position_key()
        return self.position_history.count(current_key) >= 3

    def is_fifty_move_rule(self):
        return self.halfmove_clock >= 100

    def make_move(self, start, end, sounds=None):
        if self.promotion_pending:
            return
        piece = self.board[start[0]][start[1]]
        target_before = self.board[end[0]][end[1]]
        ptype = piece[1]
        is_pawn_move = (ptype == 'p')
        is_capture = (target_before is not None)
        is_en_passant = (ptype == 'p' and self.en_passant_target == end)
        if is_en_passant:
            is_capture = True
            captured_piece = self.board[start[0]][end[1]]
        else:
            captured_piece = target_before
        is_castle = (ptype == 'K' and abs(start[1] - end[1]) == 2)
        sound_type = None
        if is_castle:
            sound_type = 'castle'
        elif is_capture:
            sound_type = 'capture'
        else:
            sound_type = 'move'
        current_state = GameState(
            self.board, self.current_player, self.king_positions.copy(),
            self.has_moved.copy(), self.en_passant_target, self.en_passant_pawn,
            self.halfmove_clock, sound_type, (start, end),
            self.white_time, self.black_time, self.first_move_made,
            self.white_made_first, self.black_made_first,
            self.white_captured_value, self.black_captured_value,
            self.flipped
        )
        self.history.append(current_state)
        if is_capture and captured_piece:
            captured_value = get_piece_value(captured_piece)
            if self.current_player == 'w':
                self.white_captured_value += captured_value
            else:
                self.black_captured_value += captured_value
        if is_en_passant:
            captured_pawn_pos = (start[0], end[1])
            self.board[captured_pawn_pos[0]][captured_pawn_pos[1]] = None
        if is_castle:
            rook_col = 0 if end[1] < start[1] else 7
            rook_row = start[0]
            rook_start = (rook_row, rook_col)
            rook_end = (rook_row, 3 if rook_col == 0 else 5)
            rook_piece = self.board[rook_start[0]][rook_start[1]]
            self.board[rook_end[0]][rook_end[1]] = rook_piece
            self.board[rook_start[0]][rook_start[1]] = None
            rook_key = f'{self.current_player}R_{"a" if rook_start[1] == 0 else "h"}'
            self.has_moved[rook_key] = True
        self.board[end[0]][end[1]] = piece
        self.board[start[0]][start[1]] = None
        self.last_move = (start, end)
        if ptype == 'K':
            self.king_positions[self.current_player] = end
            self.has_moved[f'{self.current_player}K'] = True
        elif ptype == 'R':
            if start[1] == 0:
                self.has_moved[f'{self.current_player}R_a'] = True
            elif start[1] == 7:
                self.has_moved[f'{self.current_player}R_h'] = True
        elif ptype == 'p':
            if abs(start[0] - end[0]) == 2:
                self.en_passant_target = (start[0] + (end[0] - start[0]) // 2, start[1])
                self.en_passant_pawn = end
            else:
                self.en_passant_target = None
                self.en_passant_pawn = None
            if end[0] == 0 or end[0] == 7:
                self.promotion_pending = (end[0], end[1], piece[0])
                return
        else:
            self.en_passant_target = None
            self.en_passant_pawn = None
        if is_pawn_move or is_capture:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1
        if self.current_player == 'w' and not self.white_made_first:
            self.white_made_first = True
        elif self.current_player == 'b' and not self.black_made_first:
            self.black_made_first = True
        if self.white_made_first and self.black_made_first:
            if self.current_player == 'w':
                self.white_time += self.increment
            else:
                self.black_time += self.increment
        if sounds and sounds.get(sound_type):
            sounds[sound_type].play()
        self.current_player = 'b' if self.current_player == 'w' else 'w'
        self.selected = None
        self.valid_moves = []
        self.add_current_position_to_history()
        if self.white_made_first and self.black_made_first and self.last_tick is None:
            self.last_tick = pygame.time.get_ticks()

    def promote_pawn(self, choice, sounds=None):
        if not self.promotion_pending:
            return
        row, col, color = self.promotion_pending
        self.board[row][col] = color + choice
        self.promotion_pending = None
        self.halfmove_clock = 0
        self.current_player = 'b' if self.current_player == 'w' else 'w'
        self.selected = None
        self.valid_moves = []
        self.add_current_position_to_history()
        if sounds and sounds.get('promote'):
            sounds['promote'].play()

    def undo_move(self, sounds=None):
        if not self.history:
            return
        previous_state = self.history.pop()
        self.board = [row[:] for row in previous_state.board]
        self.current_player = previous_state.current_player
        self.king_positions = previous_state.king_positions.copy()
        self.has_moved = previous_state.has_moved.copy()
        self.en_passant_target = previous_state.en_passant_target
        self.en_passant_pawn = previous_state.en_passant_pawn
        self.halfmove_clock = previous_state.halfmove_clock
        self.promotion_pending = None
        self.selected = None
        self.valid_moves = []
        self.last_move = previous_state.last_move
        self.first_move_made = previous_state.first_move_made
        self.white_made_first = previous_state.white_made_first
        self.black_made_first = previous_state.black_made_first
        self.white_time = previous_state.white_time
        self.black_time = previous_state.black_time
        self.white_captured_value = previous_state.white_captured_value
        self.black_captured_value = previous_state.black_captured_value
        self.flipped = previous_state.flipped
        self.last_tick = pygame.time.get_ticks() if (self.white_made_first and self.black_made_first) else None
        self.game_over = False
        self.winner = None
        self.draw_offered = False
        self.resigned = False
        if self.position_history:
            self.position_history.pop()
        if sounds and previous_state.last_sound_type and sounds.get(previous_state.last_sound_type):
            sounds[previous_state.last_sound_type].play()

    def get_valid_moves(self, start):
        if self.promotion_pending:
            return []
        moves = []
        sr, sc = start
        piece = self.board[sr][sc]
        if not piece or piece[0] != self.current_player:
            return moves
        for r in range(8):
            for c in range(8):
                if self.is_valid_move(start, (r, c)):
                    board_backup = [row[:] for row in self.board]
                    king_backup = self.king_positions.copy()
                    en_passant_backup = self.en_passant_target
                    en_passant_pawn_backup = self.en_passant_pawn
                    self.board[r][c] = piece
                    self.board[sr][sc] = None
                    if piece[1] == 'K':
                        self.king_positions[piece[0]] = (r, c)
                    if piece[1] == 'p' and self.en_passant_target == (r, c):
                        self.board[sr][c] = None
                    in_check = self.is_in_check(piece[0])
                    self.board = board_backup
                    self.king_positions = king_backup
                    self.en_passant_target = en_passant_backup
                    self.en_passant_pawn = en_passant_pawn_backup
                    if not in_check:
                        moves.append((r, c))
        return moves

def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    SCREEN_WIDTH = 1323
    SCREEN_HEIGHT = 680
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("My Chess Game 🧠")

    TIME_CONTROLS = [
        (60, 0, "Bullet", "1+0"),
        (120, 1, "Bullet", "2+1"),
        (180, 0, "Blitz", "3+0"),
        (180, 2, "Blitz", "3+2"),
        (300, 0, "Blitz", "5+0"),
        (300, 3, "Blitz", "5+3"),
        (600, 0, "Rapid", "10+0"),
        (600, 5, "Rapid", "10+5"),
        (900, 10, "Rapid", "15+10"),
        (1800, 0, "Classical", "30+0"),
        (1800, 20, "Classical", "30+20"),
        ("Custom", 0, "Custom", "Custom")
    ]

    game_state = 'menu'
    game = None
    current_time_control = None

    BOARD_SIZE = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.8)
    BOARD_SIZE = (BOARD_SIZE // 8) * 8
    SQUARE_SIZE = BOARD_SIZE // 8
    COORDINATE_SPACE = max(10, SQUARE_SIZE // 5)
    BOARD_X = (SCREEN_WIDTH - BOARD_SIZE) // 2
    BOARD_Y = (SCREEN_HEIGHT - BOARD_SIZE) // 2

    BUTTON_WIDTH, BUTTON_HEIGHT = 90, 35
    BUTTON_SPACING = 10

    pieces = {}
    colors = {'w': (255, 255, 255), 'b': (0, 0, 0)}
    for color in ['w', 'b']:
        for piece in ['p', 'R', 'N', 'B', 'Q', 'K']:
            img_path = os.path.join('images', f'{color}{piece}.png')
            try:
                img = pygame.image.load(img_path)
                pieces[f'{color}{piece}'] = pygame.transform.scale(img, (SQUARE_SIZE, SQUARE_SIZE))
            except:
                surf = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                pygame.draw.circle(surf, colors[color], (SQUARE_SIZE//2, SQUARE_SIZE//2), SQUARE_SIZE//3)
                pieces[f'{color}{piece}'] = surf

    sounds = {}
    sound_files = {
        'move': 'move.wav',
        'capture': 'capture.wav',
        'castle': 'castle.wav',
        'check': 'check.wav',
        'invalid': 'invalid.wav',
        'promote': 'promote.wav'
    }
    for name, filename in sound_files.items():
        path = os.path.join('sounds', filename)
        try:
            sounds[name] = pygame.mixer.Sound(path)
            sounds[name].set_volume(0.6)
        except pygame.error as e:
            print(f"⚠️ Warning: '{filename}' not found. Sound disabled.")
            sounds[name] = None

    font = pygame.font.SysFont('Arial', 16)
    large_font = pygame.font.SysFont('Arial', 20, bold=True)
    coord_font = pygame.font.SysFont('Arial', max(10, SQUARE_SIZE // 5), bold=False)

    menu_button_width = 200
    menu_button_height = 80
    menu_buttons = []
    cols = 3
    rows = (len(TIME_CONTROLS) + cols - 1) // cols
    for i, (base, inc, cat, label) in enumerate(TIME_CONTROLS):
        row = i // cols
        col = i % cols
        x = BOARD_X + col * (menu_button_width + 10)
        y = BOARD_Y + row * (menu_button_height + 10)
        rect = pygame.Rect(x, y, menu_button_width, menu_button_height)
        menu_buttons.append((rect, base, inc, cat, label))

    button_color = (200, 0, 0)
    button_hover_color = (255, 50, 50)

    custom_input_active = False
    custom_input_text = ""
    custom_input_rect = pygame.Rect(0, 0, 200, 40)

    running = True
    check_just_played = False
    drag_start_pos = None
    drag_piece = None
    drag_valid_moves = []

    editor_active = False
    editor_dragging = None
    editor_toolbar_top = []
    editor_toolbar_bottom = []
    editor_buttons = []

    while running:
        current_time = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()

        pack1_buttons = []
        pack2_buttons = []
        editor_button = None

        if game_state == 'playing':
            pack1_y = BOARD_Y + 10
            pack1_x_start = BOARD_X + BOARD_SIZE + 10
            abort_rect = pygame.Rect(pack1_x_start, pack1_y, BUTTON_WIDTH, BUTTON_HEIGHT)
            pack1_buttons.append(('abort_resign', abort_rect))
            undo_rect = pygame.Rect(pack1_x_start + BUTTON_WIDTH + BUTTON_SPACING, pack1_y, BUTTON_WIDTH, BUTTON_HEIGHT)
            pack1_buttons.append(('undo', undo_rect))
            draw_rect = pygame.Rect(pack1_x_start + 2*(BUTTON_WIDTH + BUTTON_SPACING), pack1_y, BUTTON_WIDTH, BUTTON_HEIGHT)
            pack1_buttons.append(('draw', draw_rect))

            pack2_y = BOARD_Y + 10 + BUTTON_HEIGHT + 10
            rematch_rect = pygame.Rect(pack1_x_start, pack2_y, BUTTON_WIDTH, BUTTON_HEIGHT)
            pack2_buttons.append(('rematch', rematch_rect))
            newgame_rect = pygame.Rect(pack1_x_start + BUTTON_WIDTH + BUTTON_SPACING, pack2_y, BUTTON_WIDTH, BUTTON_HEIGHT)
            pack2_buttons.append(('newgame', newgame_rect))

            editor_y = pack2_y + BUTTON_HEIGHT + 10
            editor_rect = pygame.Rect(pack1_x_start, editor_y, BUTTON_WIDTH, BUTTON_HEIGHT)
            editor_button = ('editor', editor_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos

                if game_state == 'menu':
                    if custom_input_active:
                        if custom_input_rect.collidepoint(x, y):
                            pass
                        else:
                            custom_input_active = False
                            if custom_input_text.isdigit() and int(custom_input_text) > 0:
                                minutes = int(custom_input_text)
                                game = ChessGame(base_time=minutes * 60, increment=0)
                                current_time_control = (minutes * 60, 0)
                                game_state = 'playing'
                                custom_input_text = ""
                    else:
                        clicked_custom = False
                        for rect, base, inc, cat, label in menu_buttons:
                            if rect.collidepoint(x, y):
                                if base == "Custom":
                                    custom_input_active = True
                                    custom_input_text = ""
                                    custom_input_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                                    clicked_custom = True
                                else:
                                    game = ChessGame(base_time=base, increment=inc)
                                    current_time_control = (base, inc)
                                    game_state = 'playing'
                                break

                elif editor_active:
                    if editor_dragging is None:
                        for piece, rect in editor_toolbar_top:
                            if rect.collidepoint(x, y):
                                editor_dragging = piece
                                break
                        for piece, rect in editor_toolbar_bottom:
                            if rect.collidepoint(x, y):
                                editor_dragging = piece
                                break
                        for name, rect in editor_buttons:
                            if rect.collidepoint(x, y):
                                if name == 'starting':
                                    game.board = game.create_board()
                                    game.king_positions = {'w': (7, 4), 'b': (0, 4)}
                                    game.has_moved = {
                                        'wK': False, 'wR_a': False, 'wR_h': False,
                                        'bK': False, 'bR_a': False, 'bR_h': False
                                    }
                                    game.flipped = False
                                elif name == 'clear':
                                    game.board = [[None]*8 for _ in range(8)]
                                    game.king_positions = {'w': None, 'b': None}
                                    game.has_moved = {
                                        'wK': False, 'wR_a': False, 'wR_h': False,
                                        'bK': False, 'bR_a': False, 'bR_h': False
                                    }
                                    game.flipped = False
                                elif name == 'flip':
                                    # ✅ Rotate pieces physically (no color swap)
                                    new_board = [[None] * 8 for _ in range(8)]
                                    for r in range(8):
                                        for c in range(8):
                                            piece = game.board[r][c]
                                            if piece is not None:
                                                new_board[7 - r][7 - c] = piece
                                    game.board = new_board
                                    # Update king positions
                                    new_kings = {'w': None, 'b': None}
                                    for r in range(8):
                                        for c in range(8):
                                            piece = game.board[r][c]
                                            if piece and piece[1] == 'K':
                                                new_kings[piece[0]] = (r, c)
                                    game.king_positions = new_kings
                                    # ✅ Toggle flipped flag for coordinate drawing
                                    game.flipped = not game.flipped
                                elif name == 'continue':
                                    editor_active = False
                                break
                    else:
                        col = (x - BOARD_X) // SQUARE_SIZE
                        row = (y - BOARD_Y) // SQUARE_SIZE
                        if 0 <= row < 8 and 0 <= col < 8:
                            game.board[row][col] = editor_dragging
                            if editor_dragging[1] == 'K':
                                game.king_positions[editor_dragging[0]] = (row, col)
                            editor_dragging = None

                else:
                    if game.promotion_pending:
                        promo_row, promo_col, promo_color = game.promotion_pending
                        panel_x = BOARD_X + promo_col * SQUARE_SIZE - SQUARE_SIZE // 2
                        panel_y = BOARD_Y + promo_row * SQUARE_SIZE - len(['Q','R','B','N']) * (SQUARE_SIZE + 5) - 10
                        if promo_row == 0:
                            panel_y = BOARD_Y + promo_row * SQUARE_SIZE + SQUARE_SIZE + 10
                        panel_x = max(BOARD_X, min(panel_x, SCREEN_WIDTH - SQUARE_SIZE - 10))
                        for i, p in enumerate(['Q','R','B','N']):
                            rect = pygame.Rect(panel_x, panel_y + i * (SQUARE_SIZE + 5), SQUARE_SIZE, SQUARE_SIZE)
                            if rect.collidepoint(x, y):
                                game.promote_pawn(p, sounds)
                                break
                        continue

                    for name, rect in pack1_buttons:
                        if rect.collidepoint(x, y):
                            if name == 'abort_resign':
                                if game.white_made_first and game.black_made_first:
                                    game.game_over = True
                                    game.winner = 'b' if game.current_player == 'w' else 'w'
                                else:
                                    game_state = 'menu'
                            elif name == 'undo':
                                game.undo_move(sounds)
                                check_just_played = False
                            elif name == 'draw':
                                if not game.draw_offered:
                                    game.draw_offered = True
                                else:
                                    game.game_over = True
                                    game.winner = None
                            break

                    for name, rect in pack2_buttons:
                        if rect.collidepoint(x, y):
                            if name == 'rematch':
                                if game.game_over and current_time_control:
                                    base, inc = current_time_control
                                    game = ChessGame(base_time=base, increment=inc)
                            elif name == 'newgame':
                                game_state = 'menu'
                            break

                    if editor_button and editor_button[1].collidepoint(x, y):
                        editor_active = True
                        editor_dragging = None
                        editor_toolbar_top = []
                        editor_toolbar_bottom = []
                        piece_types = ['K', 'Q', 'R', 'B', 'N', 'p']
                        for i, ptype in enumerate(piece_types):
                            rect_top = pygame.Rect(BOARD_X + i * (SQUARE_SIZE + 5), BOARD_Y - SQUARE_SIZE - 10, SQUARE_SIZE, SQUARE_SIZE)
                            editor_toolbar_top.append((f'b{ptype}', rect_top))
                            rect_bottom = pygame.Rect(BOARD_X + i * (SQUARE_SIZE + 5), BOARD_Y + BOARD_SIZE + 10, SQUARE_SIZE, SQUARE_SIZE)
                            editor_toolbar_bottom.append((f'w{ptype}', rect_bottom))
                        editor_buttons = []
                        btn_x = BOARD_X + BOARD_SIZE + 20
                        btn_y_start = BOARD_Y + 10
                        for i, name in enumerate(['starting', 'clear', 'flip', 'continue']):
                            rect = pygame.Rect(btn_x, btn_y_start + i * (BUTTON_HEIGHT + 10), BUTTON_WIDTH, BUTTON_HEIGHT)
                            editor_buttons.append((name, rect))

                    if not game.promotion_pending and not game.game_over and BOARD_X <= x < BOARD_X + BOARD_SIZE and BOARD_Y <= y < BOARD_Y + BOARD_SIZE:
                        col = (x - BOARD_X) // SQUARE_SIZE
                        row = (y - BOARD_Y) // SQUARE_SIZE
                        if 0 <= row < 8 and 0 <= col < 8:
                            piece = game.board[row][col]
                            if piece and piece[0] == game.current_player:
                                drag_start_pos = (row, col)
                                drag_piece = piece
                                drag_valid_moves = game.get_valid_moves((row, col))

            elif event.type == pygame.MOUSEBUTTONUP:
                x, y = event.pos

                if game_state == 'menu' or game.promotion_pending:
                    drag_start_pos = None
                    drag_piece = None
                    drag_valid_moves = []
                    continue

                if editor_active:
                    if editor_dragging:
                        col = (x - BOARD_X) // SQUARE_SIZE
                        row = (y - BOARD_Y) // SQUARE_SIZE
                        if 0 <= row < 8 and 0 <= col < 8:
                            game.board[row][col] = editor_dragging
                            if editor_dragging[1] == 'K':
                                game.king_positions[editor_dragging[0]] = (row, col)
                            editor_dragging = None
                else:
                    button_clicked = any(
                        (rect.collidepoint(x, y) for _, rect in pack1_buttons + pack2_buttons)
                    )
                    if editor_button:
                        button_clicked = button_clicked or editor_button[1].collidepoint(x, y)
                    if button_clicked:
                        drag_start_pos = None
                        drag_piece = None
                        drag_valid_moves = []
                    else:
                        if not game.promotion_pending and not game.game_over and BOARD_X <= x < BOARD_X + BOARD_SIZE and BOARD_Y <= y < BOARD_Y + BOARD_SIZE:
                            col = (x - BOARD_X) // SQUARE_SIZE
                            row = (y - BOARD_Y) // SQUARE_SIZE
                            if 0 <= row < 8 and 0 <= col < 8:
                                was_drag = bool(drag_start_pos and (row, col) != drag_start_pos)
                                if was_drag:
                                    if (row, col) in drag_valid_moves:
                                        game.make_move(drag_start_pos, (row, col), sounds)
                                    else:
                                        if sounds and sounds.get('invalid'):
                                            sounds['invalid'].play()
                                else:
                                    if game.selected is None:
                                        piece = game.board[row][col]
                                        if piece and piece[0] == game.current_player:
                                            game.selected = (row, col)
                                            game.valid_moves = game.get_valid_moves((row, col))
                                    else:
                                        if (row, col) in game.valid_moves:
                                            game.make_move(game.selected, (row, col), sounds)
                                        else:
                                            piece = game.board[row][col]
                                            if piece and piece[0] == game.current_player:
                                                game.selected = (row, col)
                                                game.valid_moves = game.get_valid_moves((row, col))
                                            else:
                                                if sounds and sounds.get('invalid'):
                                                    sounds['invalid'].play()
                                                game.selected = None
                                                game.valid_moves = []
                                drag_start_pos = None
                                drag_piece = None
                                drag_valid_moves = []

            elif event.type == pygame.KEYDOWN:
                if custom_input_active:
                    if event.key == pygame.K_RETURN:
                        if custom_input_text.isdigit() and int(custom_input_text) > 0:
                            minutes = int(custom_input_text)
                            game = ChessGame(base_time=minutes * 60, increment=0)
                            current_time_control = (minutes * 60, 0)
                            game_state = 'playing'
                            custom_input_active = False
                            custom_input_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        custom_input_text = custom_input_text[:-1]
                    elif event.unicode.isdigit():
                        custom_input_text += event.unicode

                elif editor_active and event.key == pygame.K_ESCAPE:
                    editor_active = False

        screen.fill((210, 180, 140))

        if game_state == 'menu':
            if custom_input_active:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                screen.blit(overlay, (0, 0))
                prompt = large_font.render("Enter time (minutes):", True, (255, 255, 255))
                screen.blit(prompt, (SCREEN_WIDTH//2 - prompt.get_width()//2, SCREEN_HEIGHT//2 - 50))
                pygame.draw.rect(screen, (255, 255, 255), custom_input_rect)
                pygame.draw.rect(screen, (0, 0, 0), custom_input_rect, 2)
                txt_surface = large_font.render(custom_input_text, True, (0, 0, 0))
                screen.blit(txt_surface, (custom_input_rect.x + 5, custom_input_rect.y + 5))
            else:
                title = large_font.render("Select Time Control", True, (0, 0, 0))
                screen.blit(title, (BOARD_X, BOARD_Y - 50))
                for rect, base, inc, cat, label in menu_buttons:
                    btn_color = (100, 100, 100)
                    if rect.collidepoint(mouse_pos):
                        btn_color = (150, 150, 150)
                    pygame.draw.rect(screen, btn_color, rect)
                    pygame.draw.rect(screen, (0, 0, 0), rect, 2)
                    text = font.render(label, True, (255, 255, 255))
                    cat_text = font.render(cat, True, (255, 255, 255))
                    screen.blit(text, (rect.centerx - text.get_width()//2, rect.y + 10))
                    screen.blit(cat_text, (rect.centerx - cat_text.get_width()//2, rect.y + 40))

        elif editor_active:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            for row in range(8):
                for col in range(8):
                    color = (240, 217, 181) if (row + col) % 2 == 0 else (181, 136, 99)
                    x = BOARD_X + col * SQUARE_SIZE
                    y = BOARD_Y + row * SQUARE_SIZE
                    pygame.draw.rect(screen, color, (x, y, SQUARE_SIZE, SQUARE_SIZE))

                    # ✅ Coordinate drawing from your correct version (1766923972180.txt)
                    if game.flipped:
                        if row == 7:
                            file_text = chr(ord('h') - col)
                            file_surf = coord_font.render(file_text, True, (0, 0, 0))
                            screen.blit(file_surf, (x + 2, y + SQUARE_SIZE - file_surf.get_height() - 2))
                        if col == 7:
                            rank_text = str(row + 1)
                            rank_surf = coord_font.render(rank_text, True, (0, 0, 0))
                            screen.blit(rank_surf, (x + SQUARE_SIZE - rank_surf.get_width() - 2, y + SQUARE_SIZE - rank_surf.get_height() - 2))
                    else:
                        if row == 7:
                            file_text = chr(ord('a') + col)
                            file_surf = coord_font.render(file_text, True, (0, 0, 0))
                            screen.blit(file_surf, (x + 2, y + SQUARE_SIZE - file_surf.get_height() - 2))
                        if col == 7:
                            rank_text = str(8 - row)
                            rank_surf = coord_font.render(rank_text, True, (0, 0, 0))
                            screen.blit(rank_surf, (x + SQUARE_SIZE - rank_surf.get_width() - 2, y + SQUARE_SIZE - rank_surf.get_height() - 2))

                    if game.board[row][col]:
                        screen.blit(pieces[game.board[row][col]], (x, y))

            for piece, rect in editor_toolbar_top:
                screen.blit(pieces[piece], (rect.x, rect.y))
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
            for piece, rect in editor_toolbar_bottom:
                screen.blit(pieces[piece], (rect.x, rect.y))
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)

            for name, rect in editor_buttons:
                btn_color = button_hover_color if rect.collidepoint(mouse_pos) else button_color
                pygame.draw.rect(screen, btn_color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
                btn_text = font.render(name.replace('_', ' ').upper(), True, (255, 255, 255))
                screen.blit(btn_text, (rect.centerx - btn_text.get_width()//2, rect.centery - btn_text.get_height()//2))

            if editor_dragging:
                mx, my = pygame.mouse.get_pos()
                screen.blit(pieces[editor_dragging], (mx - SQUARE_SIZE//2, my - SQUARE_SIZE//2))

        else:
            if not game.game_over and not game.promotion_pending and game.white_made_first and game.black_made_first:
                if game.last_tick is not None:
                    elapsed = (current_time - game.last_tick) / 1000.0
                    if game.current_player == 'w':
                        game.white_time -= elapsed
                        if game.white_time <= 0:
                            game.game_over = True
                            game.winner = 'b'
                    else:
                        game.black_time -= elapsed
                        if game.black_time <= 0:
                            game.game_over = True
                            game.winner = 'w'
                    game.last_tick = current_time

            game_result = None
            in_check = False
            if not game.promotion_pending and not game.game_over:
                current = game.current_player
                in_check = game.is_in_check(current)
                if game.is_checkmate(current):
                    game.game_over = True
                    game.winner = 'b' if current == 'w' else 'w'
                elif game.is_stalemate(current):
                    game_result = 'stalemate'
                elif game.is_insufficient_material():
                    game_result = 'insufficient'
                elif game.is_threefold_repetition():
                    game_result = 'threefold'
                elif game.is_fifty_move_rule():
                    game_result = 'fifty-move'

            for row in range(8):
                for col in range(8):
                    color = (240, 217, 181) if (row + col) % 2 == 0 else (181, 136, 99)
                    x = BOARD_X + col * SQUARE_SIZE
                    y = BOARD_Y + row * SQUARE_SIZE
                    pygame.draw.rect(screen, color, (x, y, SQUARE_SIZE, SQUARE_SIZE))

                    # ✅ Coordinate drawing from your correct version (1766923972180.txt)
                    if game.flipped:
                        if row == 7:
                            file_text = chr(ord('h') - col)
                            file_surf = coord_font.render(file_text, True, (0, 0, 0))
                            screen.blit(file_surf, (x + 2, y + SQUARE_SIZE - file_surf.get_height() - 2))
                        if col == 7:
                            rank_text = str(row + 1)
                            rank_surf = coord_font.render(rank_text, True, (0, 0, 0))
                            screen.blit(rank_surf, (x + SQUARE_SIZE - rank_surf.get_width() - 2, y + SQUARE_SIZE - rank_surf.get_height() - 2))
                    else:
                        if row == 7:
                            file_text = chr(ord('a') + col)
                            file_surf = coord_font.render(file_text, True, (0, 0, 0))
                            screen.blit(file_surf, (x + 2, y + SQUARE_SIZE - file_surf.get_height() - 2))
                        if col == 7:
                            rank_text = str(8 - row)
                            rank_surf = coord_font.render(rank_text, True, (0, 0, 0))
                            screen.blit(rank_surf, (x + SQUARE_SIZE - rank_surf.get_width() - 2, y + SQUARE_SIZE - rank_surf.get_height() - 2))

                    if game.last_move:
                        start, end = game.last_move
                        if (row, col) == start:
                            pygame.draw.rect(screen, (174, 213, 129), (x, y, SQUARE_SIZE, SQUARE_SIZE))
                        elif (row, col) == end:
                            pygame.draw.rect(screen, (76, 175, 80), (x, y, SQUARE_SIZE, SQUARE_SIZE))

                    if game.selected == (row, col):
                        pygame.draw.rect(screen, (255, 255, 0), (x, y, SQUARE_SIZE, SQUARE_SIZE), 3)

                    valid_moves_to_show = game.valid_moves
                    if drag_start_pos and (row, col) != drag_start_pos:
                        valid_moves_to_show = drag_valid_moves
                    if (row, col) in valid_moves_to_show:
                        pygame.draw.circle(screen, (0, 0, 0), (x + SQUARE_SIZE//2, y + SQUARE_SIZE//2), SQUARE_SIZE//6, 2)

                    if (row, col) in game.king_positions.values():
                        owner = game.board[row][col][0] if game.board[row][col] else None
                        if owner and game.is_in_check(owner):
                            pygame.draw.rect(screen, (255, 0, 0), (x, y, SQUARE_SIZE, SQUARE_SIZE), 3)

            # Draw pieces from physical board (already rotated)
            for row in range(8):
                for col in range(8):
                    piece = game.board[row][col]
                    if piece:
                        x = BOARD_X + col * SQUARE_SIZE
                        y = BOARD_Y + row * SQUARE_SIZE
                        if drag_piece and drag_start_pos == (row, col):
                            ghost = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                            ghost.blit(pieces[piece], (0, 0))
                            ghost.fill((255, 255, 255, 128), special_flags=pygame.BLEND_RGBA_MULT)
                            screen.blit(ghost, (x, y))
                        else:
                            screen.blit(pieces[piece], (x, y))

            if drag_piece and drag_start_pos:
                mx, my = pygame.mouse.get_pos()
                screen.blit(pieces[drag_piece], (mx - SQUARE_SIZE//2, my - SQUARE_SIZE//2))

            if game.promotion_pending:
                promo_row, promo_col, promo_color = game.promotion_pending
                panel_x = BOARD_X + promo_col * SQUARE_SIZE - SQUARE_SIZE // 2
                panel_y = BOARD_Y + promo_row * SQUARE_SIZE - 4 * (SQUARE_SIZE + 5) - 10
                if promo_row == 0:
                    panel_y = BOARD_Y + promo_row * SQUARE_SIZE + SQUARE_SIZE + 10
                panel_x = max(BOARD_X, min(panel_x, SCREEN_WIDTH - SQUARE_SIZE - 10))
                overlay = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 80))
                screen.blit(overlay, (BOARD_X, BOARD_Y))
                for i, p in enumerate(['Q','R','B','N']):
                    piece_key = promo_color + p
                    rect = pygame.Rect(panel_x, panel_y + i * (SQUARE_SIZE + 5), SQUARE_SIZE, SQUARE_SIZE)
                    if rect.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, (220, 220, 220), rect)
                    screen.blit(pieces[piece_key], (rect.x, rect.y))
                    pygame.draw.rect(screen, (255, 255, 255), rect, 1)

            if game.game_over:
                if game.winner:
                    text = f"{game.winner.capitalize()} wins!"
                    color = (0, 0, 255) if game.winner == 'w' else (0, 0, 0)
                else:
                    text = "Game drawn"
                    color = (128, 0, 128)
            elif game.draw_offered:
                text = "Draw offered"
                color = (128, 0, 128)
            elif game.promotion_pending:
                text = f"{'White' if game.promotion_pending[2] == 'w' else 'Black'}: Choose promotion piece"
                color = (255, 165, 0)
            elif game_result == 'stalemate':
                text = "Draw by stalemate!"
                color = (0, 128, 0)
            elif game_result == 'insufficient':
                text = "Draw by insufficient material!"
                color = (128, 0, 128)
            elif game_result == 'threefold':
                text = "Draw by threefold repetition!"
                color = (128, 0, 128)
            elif game_result == 'fifty-move':
                text = "Draw by 50-move rule!"
                color = (128, 0, 128)
            else:
                text = f"{'White' if game.current_player == 'w' else 'Black'} to move"
                color = (0, 0, 0)

            status_surf = font.render(text, True, color)
            screen.blit(status_surf, (BOARD_X, BOARD_Y - 40))

            if not game.game_over and not game.promotion_pending and in_check:
                check_surf = font.render("CHECK!", True, (255, 0, 0))
                screen.blit(check_surf, (BOARD_X, BOARD_Y - 20))

            net_advantage = game.white_captured_value - game.black_captured_value
            white_time_str = f"{max(0, int(game.white_time // 60)):02}:{max(0, int(game.white_time % 60)):02}"
            black_time_str = f"{max(0, int(game.black_time // 60)):02}:{max(0, int(game.black_time % 60)):02}"
            white_time_surf = large_font.render(white_time_str, True, (0, 0, 0))
            black_time_surf = large_font.render(black_time_str, True, (0, 0, 0))
            white_material_str = f" +{net_advantage}" if net_advantage > 0 else ""
            black_material_str = f" +{-net_advantage}" if net_advantage < 0 else ""
            white_material_surf = large_font.render(white_material_str, True, (0, 0, 0))
            black_material_surf = large_font.render(black_material_str, True, (0, 0, 0))

            WHITE_CLOCK_X = BOARD_X - COORDINATE_SPACE
            WHITE_CLOCK_Y = BOARD_Y + BOARD_SIZE + 10
            BLACK_CLOCK_X = BOARD_X + BOARD_SIZE + 10
            BLACK_CLOCK_Y = BOARD_Y - 40

            pad = 4
            white_rect = white_time_surf.get_rect()
            white_rect.inflate_ip(pad*2, pad*2)
            white_rect.topleft = (WHITE_CLOCK_X - pad, WHITE_CLOCK_Y - pad)
            pygame.draw.rect(screen, (0, 0, 0), white_rect, 3)
            screen.blit(white_time_surf, (WHITE_CLOCK_X, WHITE_CLOCK_Y))
            if white_material_str:
                screen.blit(white_material_surf, (WHITE_CLOCK_X + white_time_surf.get_width() + 6, WHITE_CLOCK_Y))

            black_rect = black_time_surf.get_rect()
            black_rect.inflate_ip(pad*2, pad*2)
            black_rect.topleft = (BLACK_CLOCK_X - pad, BLACK_CLOCK_Y - pad)
            pygame.draw.rect(screen, (0, 0, 0), black_rect, 3)
            screen.blit(black_time_surf, (BLACK_CLOCK_X, BLACK_CLOCK_Y))
            if black_material_str:
                screen.blit(black_material_surf, (BLACK_CLOCK_X + black_time_surf.get_width() + 6, BLACK_CLOCK_Y))

            all_buttons = pack1_buttons + pack2_buttons
            for name, rect in all_buttons:
                if name == 'rematch' and not game.game_over:
                    continue
                if name == 'abort_resign':
                    label = "Resign" if (game.white_made_first and game.black_made_first) else "Abort"
                elif name == 'undo':
                    label = "Undo"
                elif name == 'draw':
                    label = "Draw"
                elif name == 'rematch':
                    label = "Rematch"
                elif name == 'newgame':
                    label = "New Game"
                btn_color = button_hover_color if rect.collidepoint(mouse_pos) else button_color
                pygame.draw.rect(screen, btn_color, rect)
                pygame.draw.rect(screen, (0, 0, 0), rect, 1)
                btn_text = font.render(label, True, (255, 255, 255))
                screen.blit(btn_text, (rect.centerx - btn_text.get_width()//2, rect.centery - btn_text.get_height()//2))

            if editor_button is not None:
                editor_btn_color = button_hover_color if editor_button[1].collidepoint(mouse_pos) else button_color
                pygame.draw.rect(screen, editor_btn_color, editor_button[1])
                pygame.draw.rect(screen, (0, 0, 0), editor_button[1], 1)
                editor_btn_text = font.render("Editor", True, (255, 255, 255))
                screen.blit(editor_btn_text, (editor_button[1].centerx - editor_btn_text.get_width()//2, editor_button[1].centery - editor_btn_text.get_height()//2))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()