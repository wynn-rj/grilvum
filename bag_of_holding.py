"""A extension that adds party funds utilities"""
import sqlite3
from discord.ext import commands
from utils.config_reader import YAMLConfigReader
from utils.logger import Logger

class BagOfHolding(commands.Cog):
    """Extension class"""
    def __init__(self, bot):
        self.bot = bot
        self.config = YAMLConfigReader()

    def get_party_bag(self, guild):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Item, Quantity FROM bag_of_holding WHERE Guild_ID IS ?",
                        (guild.id,))
            result = cur.fetchall()
        finally:
            conn.close()
        return result if len(result) > 0 else None

    def add_to_bag(self, guild, item, quantity):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Quantity FROM bag_of_holding WHERE Item IS ? AND Guild_ID = ?",
                        (item, guild.id))
            result = cur.fetchone()
            if result is not None:
                cur.execute("UPDATE bag_of_holding SET Quantity = ? WHERE Item IS ? AND Guild_ID = ?",
                            (int(result[0]) + int(quantity), item, guild.id))

            else:
                cur.execute("INSERT INTO bag_of_holding (Guild_ID, Item, Quantity) VALUES(?,?,?)",
                            (guild.id, item, quantity))
            conn.commit()
        finally:
            conn.close()

    def remove_from_bag(self, guild, item, quantity):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Quantity FROM bag_of_holding WHERE Item IS ? AND Guild_ID = ?",
                        (item, guild.id))
            result = cur.fetchone()
            if result is not None:
                if int(result[0]) - int(quantity) < 1:
                    cur.execute("DELETE FROM bag_of_holding WHERE Item = ? AND Guild_ID = ?",
                                (item, guild.id))
                else:
                    cur.execute("UPDATE bag_of_holding SET Quantity = ? WHERE Item IS ? AND Guild_ID = ?",
                                (int(result[0]) - int(quantity), item, guild.id))
            else:
                return 0
            conn.commit()
            return 1
        finally:
            conn.close()

    @commands.group(pass_context=True, help="Manage bag of holding")
    async def bagOfHolding(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid subcommand')

    @bagOfHolding.command()
    async def addItem(self, ctx, item: str):
        self.add_to_bag(ctx.guild, item, 1)
        await ctx.send(f'{item} successfully added to the Bag of Holding')

    @bagOfHolding.command()
    async def addItems(self, ctx, item: str, quantity):
        self.add_to_bag(ctx.guild, item, quantity)
        await ctx.send(f'{item}({quantity}) successfully added to the Bag of Holding')

    @bagOfHolding.command()
    async def dump(self, ctx):
        party_bag = self.get_party_bag(ctx.guild)
        if party_bag is None:
            await ctx.send('Failed to get party Bag of Holding')
            return

        print_string = 'The Bag of Holding Contains:'
        for item in party_bag:
            print_string += f'\n{item[0]}'
            if item[1] > 1:
                print_string += f': {item[1]}'

        await ctx.send(print_string)

    @bagOfHolding.command()
    async def removeItem(self, ctx, item: str):
        result = self.remove_from_bag(ctx.guild, item, 1)
        await ctx.send(f'{item} removed from the Bag of Holding')
        if result == 1:
            await ctx.send(f'{item} removed from the Bag of Holding')
        else:
            await ctx.send(f'{item} not found')

    @bagOfHolding.command()
    async def removeItems(self, ctx, item: str, quantity):
        result = self.remove_from_bag(ctx.guild, item, quantity)
        if result == 1:
            await ctx.send(f'{item}({quantity}) removed from the Bag of Holding')
        else:
            await ctx.send(f'{item} not found')

    @bagOfHolding.command(hidden=True)
    async def fix(self, ctx):
        admins = YAMLConfigReader('/config/administration.yml').data.admins
        if not str(ctx.author) in admins:
            return
        await ctx.send('Fix run on server')

def setup(bot):
    """Add the extension as a cog"""
    bot.add_cog(BagOfHolding(bot))
