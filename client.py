import sys
import os
import pygame
import requests

API_BASE_URL = "https://work-dt8p.onrender.com"

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)    # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色

pygame.init()
WIDTH, HEIGHT = 700, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 16)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.message = "Press ENTER to submit, R to restart, H for Hard Mode"
        self.guess_history = []
        self.stats = {"total": 0, "wins": 0, "win_rate": 0.0}
        self.hard_mode = False  # 任務四：預設為 Normal 模式
        self.start_new_game()

    def start_new_game(self):
        """ 向 FastAPI 伺服器請求建立新的一局，可帶入 hard_mode """
        try:
            payload = {"hard_mode": self.hard_mode}
            res = requests.post(f"{API_BASE_URL}/api/new-game", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.guess_history = []
                if "stats" in data:
                    self.stats = data["stats"]
                mode_str = "HARD" if self.hard_mode else "Normal"
                self.message = f"New game started! Mode: {mode_str}"
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"

    def submit_guess(self):
        """ 將當前行單字發送至 FastAPI 驗證 """
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)
            
            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                
                self.guess_history.append(guess_word)

                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                if "stats" in data:
                    self.stats = data["stats"]

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press R to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    if self.row == 6 or data.get("is_game_over", False):
                        target_word = data.get("target_word", "UNKNOWN")
                        self.message = f"Game Over! The word was {target_word}. Press R to restart."
                        self.game_over = True
                    else:
                        tries_left = data.get("tries_left", 6 - self.row)
                        self.message = f"Keep guessing! ({tries_left} tries left)"
            else:
                error_detail = res.json().get("detail", "Error processing guess")
                # 任務四：捕捉硬核模式提示錯誤訊息並友善顯示
                if "Hard Mode" in error_detail:
                    self.message = "Hard Mode: Must use green hints!"
                elif error_detail == "Word not in dictionary":
                    self.message = "Not in word list!"
                else:
                    self.message = error_detail
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        if event.key == pygame.K_r:
            self.start_new_game()
            return

        # 任務四：按下 H 鍵切換硬核模式開關並重新開始
        if event.key == pygame.K_h:
            self.hard_mode = not self.hard_mode
            self.start_new_game()
            return

        if self.game_over:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
        elif event.key == pygame.K_RETURN:
            self.submit_guess()
        elif event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        margin_x, margin_y = 75, 50
        box_size = 60
        gap = 10

        # 1. 繪製 6x5 網格
        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 2. 繪製右側側邊欄（x: 500 ~ 700）
        pygame.draw.line(surface, (80, 80, 80), (500, 0), (500, HEIGHT), 2)

        # 任務四：在右上角顯示目前模式
        mode_str = "Mode: HARD" if self.hard_mode else "Mode: Normal"
        mode_surface = small_font.render(mode_str, True, (255, 100, 100) if self.hard_mode else COLOR_TEXT)
        surface.blit(mode_surface, (515, 30))

        # 顯示勝率統計資訊
        stat_text = f"Total: {self.stats.get('total', 0)} | Wins: {self.stats.get('wins', 0)} | Win Rate: {self.stats.get('win_rate', 0.0):.1f}%"
        stat_surface = small_font.render(stat_text, True, COLOR_TEXT)
        surface.blit(stat_surface, (515, 65))

        pygame.draw.line(surface, (80, 80, 80), (510, 100), (690, 100), 1)

        # 顯示歷史紀錄面板標題與已猜單字列表
        history_title = small_font.render("Guess History:", True, COLOR_TEXT)
        surface.blit(history_title, (515, 120))

        for idx, word in enumerate(self.guess_history):
            word_surface = small_font.render(f"{idx+1}. {word}", True, COLOR_TEXT)
            surface.blit(word_surface, (515, 155 + idx * 30))

        # 3. 畫底部提示訊息
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(WIDTH // 2 - 100, HEIGHT - 40))
        surface.blit(msg_surface, msg_rect)


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    window_width = WIDTH
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()
