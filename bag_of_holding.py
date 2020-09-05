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

    def get_party_bag(self, guild, name):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Item, Quantity FROM bag_of_holding_items " \
                        "WHERE Bag_ID IN (SELECT ID FROM bag_of_holding " \
                        "WHERE Name = ? and Guild_ID = ?)", (name, guild.id))
            result = cur.fetchall()
            conn.commit()
        finally:
            conn.close()
        return result

    def create_bag(self, guild, name):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT ID FROM bag_of_holding WHERE Guild_ID = ? " \
                        "AND Name = ?", (guild.id, name))
            result = cur.fetchall()
            if not result:
                cur.execute("INSERT INTO bag_of_holding VALUES (NULL, ?, ?)",
                            (guild.id, name))
                conn.commit()
                return 1
            return 2
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    def delete_bag(self, guild, name):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT ID FROM bag_of_holding WHERE Guild_ID = ? " \
                        "AND Name = ?", (guild.id, name))
            result = cur.fetchall()
            if result:
                cur.execute("DELETE FROM bag_of_holding_items WHERE Bag_ID = " \
                            "(SELECT ID FROM bag_of_holding WHERE Name = ? " \
                            "and Guild_ID = ?)", (name, guild.id))
                cur.execute("DELETE FROM bag_of_holding WHERE Name = ? AND " \
                            "Guild_ID = ?", (name, guild.id))
                conn.commit()
                return 1
            return 2
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

    def add_to_bag(self, guild, name, item, quantity: int):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Quantity FROM bag_of_holding_items WHERE " \
                        "Item = ? AND Bag_ID IN (SELECT ID FROM " \
                        "bag_of_holding WHERE Name = ? and Guild_ID = ?)",
                        (item, name, guild.id))
            result = cur.fetchone()
            if result is not None:
                cur.execute("UPDATE bag_of_holding_items SET Quantity = ? " \
                            "WHERE Item = ? AND Bag_ID IN (SELECT ID FROM " \
                            "bag_of_holding WHERE Name = ? and Guild_ID = ?)",
                            (int(result[0]) + quantity, item, name, guild.id))
            else:
                cur.execute("SELECT ID FROM bag_of_holding WHERE Name = ? " \
                            "AND Guild_ID = ?", (name, guild.id))
                bag_id = cur.fetchone()
                if bag_id is None:
                    return 0
                cur.execute("INSERT INTO bag_of_holding_items VALUES " \
                            "(NULL, ?, ?, ?)", (bag_id[0], item, quantity))
            conn.commit()
            return 1
        finally:
            conn.close()

    def remove_from_bag(self, guild, name, item, quantity: int):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Quantity FROM bag_of_holding_items WHERE " \
                        "Item = ? AND Bag_ID = (SELECT ID FROM " \
                        "bag_of_holding WHERE Name = ? and Guild_ID = ?)",
                        (item, name, guild.id))
            result = cur.fetchone()
            if not result :
                return 0
            dif = int(result[0]) - quantity
            if dif < 1:
                cur.execute("DELETE FROM bag_of_holding_items WHERE Item = ? " \
                            "AND Bag_ID = (SELECT ID FROM bag_of_holding " \
                            "WHERE Name = ? and Guild_ID = ?)",
                            (item, name, guild.id))
                removed = result[0]
            else:
                cur.execute("UPDATE bag_of_holding_items SET Quantity = ? " \
                            "WHERE Item = ? AND Bag_ID = (SELECT ID " \
                            "FROM bag_of_holding WHERE Name = ? and " \
                            "Guild_ID = ?)", (dif, item, name, guild.id))
                removed = quantity
            conn.commit()
            return removed
        finally:
            conn.close()

    @commands.group(pass_context=True, help="Manage bag of holding")
    async def boh(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid subcommand')

    @boh.group(pass_context=True, help="Add a bag or item")
    async def add(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid subcommand')

    @boh.group(pass_context=True, help="Add a bag or item")
    async def remove(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid subcommand')

    @add.command(name='bag')
    async def add_bag(self, ctx, name):
        result = self.create_bag(ctx.guild, name)
        if result == 1:
            await ctx.send(f'Added bag {name} to your party')
        elif result == 2:
            await ctx.send(f'{name} already exists.')
        else:
            await ctx.send(f'Error adding {name} to your party.')

    @remove.command(name='bag')
    async def remove_bag(self, ctx, name):
        result = self.delete_bag(ctx.guild, name)
        if result == 1:
            await ctx.send(f'Removed bag {name} from your party')
        elif result == 2:
            await ctx.send(f'{name} not found')
        else:
            await ctx.send(f'Error removing bag {name} from your party')

    async def parse_item_args(self, ctx, args, extra):
        name = item = None
        quantity = 1
        print_usage = True

        if 2 <= len(args) <= 4:
            item = args[0]
            name = args[-1]
            print_usage = False

        if len(args) == 3:
            if str(args[1]).isdigit():
                quantity = int(args[1])
            elif str(args[1]).lower() != extra:
                print_usage = True
        elif len(args) == 4:
            if str(args[1]).isdigit() and str(args[2]).lower() == extra:
                quantity = int(args[1])
            else:
                print_usage = True

        if print_usage:
            await ctx.send(
                f'usage: `boh add item <item> [amt] [{extra}] <bag>`')
            return None, None, None
        return name, item, quantity

    @add.command(name='item')
    async def add_item(self, ctx, *args):
        name, item, quantity = await self.parse_item_args(ctx, args, 'to')
        if not name:
            return
        result = self.add_to_bag(ctx.guild, name, item, quantity)
        if result == 1:
            if quantity > 1:
                await ctx.send(f'{quantity} {item}s added to {name}')
            else:
                await ctx.send(f'1 {item} added to {name}')
        else:
            await ctx.send(f'Error adding {item}({quantity}) to {name}')

    @remove.command(name='item')
    async def remove_item(self, ctx, *args):
        name, item, quantity = await self.parse_item_args(ctx, args, 'from')
        if not name:
            return
        result = self.remove_from_bag(ctx.guild, name, item, quantity)
        if result > 0:
            if quantity > 1:
                await ctx.send(f'{quantity} {item}s removed from {name}')
            else:
                await ctx.send(f'1 {item} removed from {name}')
        else:
            await ctx.send(f'{item} not found')

    @boh.command()
    async def dump(self, ctx, name):
        party_bag = self.get_party_bag(ctx.guild, name)
        if party_bag is None:
            await ctx.send(f'Failed to get {name}')
            return
        if not party_bag:
            await ctx.send(f'{name} is empty')
            return
        print_string = 'The Bag of Holding Contains:'
        for item in party_bag:
            print_string += f'\n{item[0]}'
            if item[1] > 1:
                print_string += f': {item[1]}'
        await ctx.send(print_string)

def setup(bot):
    """Add the extension as a cog"""
    bot.add_cog(BagOfHolding(bot))
