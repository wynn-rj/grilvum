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

    def add_to_bag(self, guild, item):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Quantity FROM bag_of_holding WHERE Item IS ? AND Guild_ID = ?",
                        (item, guild.id))
            result = cur.fetchone()
            if result != None:
                cur.execute("UPDATE bag_of_holding SET Quantity = ? WHERE Item IS ? AND Guild_ID = ?",
                            (result[0] + 1,item, guild.id))

            else:
                cur.execute("INSERT INTO bag_of_holding (Guild_ID, Item, Quantity) VALUES(?,?,?)",
                            (guild.id, item, 1))
            conn.commit()
        finally:
            conn.close()
    def remove_from_bag(self, guild, item):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Quantity FROM bag_of_holding WHERE Item IS ? AND Guild_ID = ?",
                        (item, guild.id))
            result = cur.fetchone()
            if result != None:
                if result[0] <= 1:
                    cur.execute("DELETE FROM bag_of_holding WHERE Item = ? AND Guild_ID = ?",
                                (item, guild.id))
                else:
                    cur.execute("UPDATE bag_of_holding SET Quantity = ? WHERE Item IS ? AND Guild_ID = ?",
                                (result[0] -1,item, guild.id))
            conn.commit()
        finally:
            conn.close()

    @commands.group(pass_context=True, help="Manage bag of holding")
    async def items(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid subcommand')

    @items.command()
    async def putInBag(self, ctx, item: str):
        self.add_to_bag(ctx.guild, item)
        await ctx.send(f'{item} successfully added to bag of holding')

    @items.command()
    async def dump(self, ctx):
        party_bag = self.get_party_bag(ctx.guild)
        if party_bag is None:
            await ctx.send('Failed to get party bag of holding')
            return
        else:
            await ctx.send('Successfully got the party bag of holding')

        print_string = ''
        for item in party_bag:
            print_string += f'Bag currently holds:\n{item[0]}: {item[1]}\n'
        await ctx.send(print_string)

    @items.command()
    async def removeFromBag(self, ctx, item: str):
        self.remove_from_bag(ctx.guild, item)
        await ctx.send(f'{item} removed from the bag of holding')

    @items.command(hidden=True)
    async def fix(self, ctx):
        admins = YAMLConfigReader('/config/administration.yml').data.admins
        if not str(ctx.author) in admins:
            return
        await ctx.send('Fix run on server')

def setup(bot):
    """Add the extension as a cog"""
    bot.add_cog(BagOfHolding(bot))
